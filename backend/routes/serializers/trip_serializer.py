"""
Trip serializers for routes app.

Contains serializers for Trip model including input validation,
output formatting, and specialized serializers for different use cases.
"""

from rest_framework import serializers
from django.core.validators import MinValueValidator, MaxValueValidator
from ..models import Trip
from common.validators import validate_trip_locations


class TripSerializer(serializers.ModelSerializer):
    """
    Standard Trip serializer for general CRUD operations.

    Handles basic Trip model serialization with all standard fields.
    Used for listing trips and basic trip details.
    """

    # Read-only computed fields
    available_cycle_hours = serializers.ReadOnlyField()
    has_coordinates = serializers.ReadOnlyField()

    # Custom field formatting
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    updated_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = Trip
        fields = [
            "id",
            "driver_name",
            "status",
            "created_at",
            "updated_at",
            "current_location",
            "current_lat",
            "current_lng",
            "pickup_location",
            "pickup_lat",
            "pickup_lng",
            "dropoff_location",
            "dropoff_lat",
            "dropoff_lng",
            "current_cycle_used",
            "available_cycle_hours",
            "total_distance_miles",
            "estimated_driving_time_hours",
            "has_coordinates",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "available_cycle_hours",
            "has_coordinates",
        ]

    def validate_current_cycle_used(self, value):
        """Validate current cycle hours are within HOS limits."""
        if value < 0:
            raise serializers.ValidationError("Current cycle hours cannot be negative")
        if value > 70:
            raise serializers.ValidationError(
                "Current cycle hours cannot exceed 70 hours (8-day limit)"
            )
        return value

    def validate(self, data):
        """Perform cross-field validation."""
        # Validate trip locations if provided
        current_loc = data.get("current_location", "")
        pickup_loc = data.get("pickup_location", "")
        dropoff_loc = data.get("dropoff_location", "")

        location_errors = validate_trip_locations(current_loc, pickup_loc, dropoff_loc)
        if location_errors:
            raise serializers.ValidationError({"locations": location_errors})

        # Validate coordinates if provided
        lat_fields = ["current_lat", "pickup_lat", "dropoff_lat"]
        lng_fields = ["current_lng", "pickup_lng", "dropoff_lng"]

        for lat_field in lat_fields:
            if lat_field in data and data[lat_field] is not None:
                lat_value = float(data[lat_field])
                if not (-90 <= lat_value <= 90):
                    raise serializers.ValidationError(
                        {lat_field: "Latitude must be between -90 and 90 degrees"}
                    )

        for lng_field in lng_fields:
            if lng_field in data and data[lng_field] is not None:
                lng_value = float(data[lng_field])
                if not (-180 <= lng_value <= 180):
                    raise serializers.ValidationError(
                        {lng_field: "Longitude must be between -180 and 180 degrees"}
                    )

        return data


class TripCreateSerializer(serializers.ModelSerializer):
    """
    Specialized serializer for creating new trips.

    Focuses only on required fields for trip creation and provides
    enhanced validation for the trip planning process.
    """

    # Required fields with custom validation
    current_cycle_used = serializers.DecimalField(
        max_digits=4,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(70)],
        help_text="Current hours used in 8-day cycle (0-70)",
    )

    class Meta:
        model = Trip
        fields = [
            "driver_name",
            "current_location",
            "current_lat",
            "current_lng",
            "pickup_location",
            "pickup_lat",
            "pickup_lng",
            "dropoff_location",
            "dropoff_lat",
            "dropoff_lng",
            "current_cycle_used",
        ]

    def validate_driver_name(self, value):
        """Validate driver name is provided and reasonable."""
        if not value or not value.strip():
            raise serializers.ValidationError("Driver name is required")
        if len(value.strip()) < 2:
            raise serializers.ValidationError(
                "Driver name must be at least 2 characters"
            )
        if len(value.strip()) > 100:
            raise serializers.ValidationError(
                "Driver name cannot exceed 100 characters"
            )
        return value.strip()

    def create(self, validated_data):
        """Create trip with default status."""
        validated_data["status"] = Trip.StatusChoices.PLANNED
        return super().create(validated_data)


class TripCalculateSerializer(serializers.Serializer):
    """
    Specialized serializer for the trip calculation endpoint.

    This is the main serializer for the POST /api/trips/calculate endpoint
    as specified in the assessment requirements.
    """

    # Required input fields from assessment
    current_location = serializers.CharField(
        max_length=255, help_text="Current driver location (address or coordinates)"
    )
    pickup_location = serializers.CharField(
        max_length=255, help_text="Pickup location address"
    )
    dropoff_location = serializers.CharField(
        max_length=255, help_text="Dropoff location address"
    )
    current_cycle_used = serializers.DecimalField(
        max_digits=4,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(70)],
        help_text="Current cycle hours used (0-70 hours)",
    )

    # Optional fields
    driver_name = serializers.CharField(
        max_length=100,
        required=False,
        default="Driver",
        help_text="Driver's name (optional)",
    )

    def validate(self, data):
        """Validate trip calculation input."""
        # Validate locations are different
        locations = [
            data["current_location"].strip().lower(),
            data["pickup_location"].strip().lower(),
            data["dropoff_location"].strip().lower(),
        ]

        if len(set(locations)) < 3:
            raise serializers.ValidationError(
                "Current location, pickup location, and dropoff location must be different"
            )

        return data

    def to_representation(self, instance):
        """
        Convert trip calculation result to API response format.

        This method formats the output for the trip calculation endpoint.
        """
        if isinstance(instance, Trip):
            # Format response with all required information
            response = {
                "trip_id": str(instance.id),
                "driver_name": instance.driver_name,
                "status": instance.status,
                "locations": {
                    "current": {
                        "address": instance.current_location,
                        "coordinates": {
                            "lat": (
                                float(instance.current_lat)
                                if instance.current_lat
                                else None
                            ),
                            "lng": (
                                float(instance.current_lng)
                                if instance.current_lng
                                else None
                            ),
                        },
                    },
                    "pickup": {
                        "address": instance.pickup_location,
                        "coordinates": {
                            "lat": (
                                float(instance.pickup_lat)
                                if instance.pickup_lat
                                else None
                            ),
                            "lng": (
                                float(instance.pickup_lng)
                                if instance.pickup_lng
                                else None
                            ),
                        },
                    },
                    "dropoff": {
                        "address": instance.dropoff_location,
                        "coordinates": {
                            "lat": (
                                float(instance.dropoff_lat)
                                if instance.dropoff_lat
                                else None
                            ),
                            "lng": (
                                float(instance.dropoff_lng)
                                if instance.dropoff_lng
                                else None
                            ),
                        },
                    },
                },
                "hos_status": {
                    "current_cycle_used": float(instance.current_cycle_used),
                    "available_cycle_hours": instance.available_cycle_hours,
                },
                "route": None,  # Will be populated by view
                "logs": [],  # Will be populated by view
                "calculated_at": instance.updated_at.isoformat(),
            }

            # Add route information if available
            if hasattr(instance, "route"):
                from .route_serializer import RouteDetailSerializer

                response["route"] = RouteDetailSerializer(instance.route).data

            # Add HOS status if available
            if hasattr(instance, "hos_status"):
                response["hos_status"].update(
                    {
                        "can_drive": instance.hos_status.can_drive,
                        "violation_reason": instance.hos_status.violation_reason,
                        "available_driving_hours": float(
                            instance.hos_status.available_driving_hours
                        ),
                        "needs_30_minute_break": instance.hos_status.needs_30_minute_break,
                    }
                )

            return response

        return super().to_representation(instance)


class TripDetailSerializer(TripSerializer):
    """
    Detailed Trip serializer with related objects.

    Includes nested route, HOS status, and logs information
    for comprehensive trip details.
    """

    # Nested serializers for related objects
    route = serializers.SerializerMethodField()
    hos_status = serializers.SerializerMethodField()
    daily_logs_count = serializers.SerializerMethodField()

    class Meta(TripSerializer.Meta):
        fields = TripSerializer.Meta.fields + [
            "route",
            "hos_status",
            "daily_logs_count",
        ]

    def get_route(self, obj):
        """Get route information if available."""
        if hasattr(obj, "route"):
            from .route_serializer import RouteDetailSerializer

            return RouteDetailSerializer(obj.route).data
        return None

    def get_hos_status(self, obj):
        """Get HOS status information if available."""
        if hasattr(obj, "hos_status"):
            return {
                "can_drive": obj.hos_status.can_drive,
                "violation_reason": obj.hos_status.violation_reason,
                "available_cycle_hours": float(obj.hos_status.available_cycle_hours),
                "available_driving_hours": float(
                    obj.hos_status.available_driving_hours
                ),
                "needs_30_minute_break": obj.hos_status.needs_30_minute_break,
                "current_duty_status": obj.hos_status.current_duty_status,
            }
        return None

    def get_daily_logs_count(self, obj):
        """Get count of daily logs for this trip."""
        return obj.daily_logs.count()


class TripStatusUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating trip status only.

    Used for status transitions like starting, completing, or cancelling trips.
    """

    class Meta:
        model = Trip
        fields = ["status"]

    def validate_status(self, value):
        """Validate status transition is allowed."""
        if self.instance:
            current_status = self.instance.status

            # Define allowed status transitions
            allowed_transitions = {
                Trip.StatusChoices.PLANNED: [
                    Trip.StatusChoices.IN_PROGRESS,
                    Trip.StatusChoices.CANCELLED,
                ],
                Trip.StatusChoices.IN_PROGRESS: [
                    Trip.StatusChoices.COMPLETED,
                    Trip.StatusChoices.CANCELLED,
                ],
                Trip.StatusChoices.COMPLETED: [],  # No transitions from completed
                Trip.StatusChoices.CANCELLED: [],  # No transitions from cancelled
            }

            if value not in allowed_transitions.get(current_status, []):
                raise serializers.ValidationError(
                    f"Cannot transition from {current_status} to {value}"
                )

        return value
