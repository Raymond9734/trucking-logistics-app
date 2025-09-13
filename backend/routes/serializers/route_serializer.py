"""
Route serializers for routes app.

Contains serializers for Route model including detailed route information
and waypoint relationships.
"""

from rest_framework import serializers
from ..models import Route


class RouteSerializer(serializers.ModelSerializer):
    """
    Standard Route serializer for basic route information.

    Used for route listings and basic route data without
    detailed waypoint information.
    """

    # Computed fields
    estimated_driving_time_hours = serializers.ReadOnlyField()
    average_speed_mph = serializers.ReadOnlyField()

    # Format timestamps
    calculated_at = serializers.DateTimeField(
        format="%Y-%m-%d %H:%M:%S", read_only=True
    )

    class Meta:
        model = Route
        fields = [
            "id",
            "total_distance_miles",
            "estimated_driving_time_minutes",
            "estimated_driving_time_hours",
            "average_speed_mph",
            "mapping_service",
            "calculated_at",
            "traffic_considered",
            "route_profile",
            "is_fastest_route",
        ]
        read_only_fields = [
            "id",
            "estimated_driving_time_hours",
            "average_speed_mph",
            "calculated_at",
        ]


class RouteDetailSerializer(RouteSerializer):
    """
    Detailed Route serializer with waypoints and comprehensive information.

    Includes all route details, waypoints, and calculated statistics
    for complete route information display.
    """

    # Nested waypoints
    waypoints = serializers.SerializerMethodField()

    # Route summary statistics
    route_summary = serializers.ReadOnlyField()
    total_time_with_stops_hours = serializers.ReadOnlyField()
    waypoints_count = serializers.SerializerMethodField()
    mandatory_stops_count = serializers.SerializerMethodField()

    # Fuel stop calculations
    requires_fuel_stops = serializers.SerializerMethodField()
    fuel_stops_count = serializers.SerializerMethodField()

    class Meta(RouteSerializer.Meta):
        fields = RouteSerializer.Meta.fields + [
            "waypoints",
            "route_summary",
            "total_time_with_stops_hours",
            "waypoints_count",
            "mandatory_stops_count",
            "requires_fuel_stops",
            "fuel_stops_count",
            "route_geometry",
        ]

    def get_waypoints(self, obj):
        """Get ordered list of waypoints for this route."""
        from .waypoint_serializer import WaypointSerializer

        waypoints = obj.waypoints.all().order_by("sequence_order")
        return WaypointSerializer(waypoints, many=True).data

    def get_waypoints_count(self, obj):
        """Get total number of waypoints."""
        return obj.waypoints.count()

    def get_mandatory_stops_count(self, obj):
        """Get number of mandatory stops."""
        return obj.waypoints.filter(is_mandatory_stop=True).count()

    def get_requires_fuel_stops(self, obj):
        """Check if route requires fuel stops."""
        return obj.requires_fuel_stops()

    def get_fuel_stops_count(self, obj):
        """Get number of required fuel stops."""
        return obj.get_fuel_stops_count()


class RouteCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new routes.

    Used internally by the route calculation service to create
    route records with calculated data.
    """

    class Meta:
        model = Route
        fields = [
            "trip",
            "total_distance_miles",
            "estimated_driving_time_minutes",
            "route_geometry",
            "mapping_service",
            "traffic_considered",
            "route_profile",
            "is_fastest_route",
            "alternative_routes_count",
        ]

    def validate_total_distance_miles(self, value):
        """Validate route distance is reasonable."""
        if value <= 0:
            raise serializers.ValidationError("Total distance must be greater than 0")
        if value > 5000:  # Reasonable upper limit for single trip
            raise serializers.ValidationError(
                "Total distance seems unreasonably large (>5000 miles)"
            )
        return value

    def validate_estimated_driving_time_minutes(self, value):
        """Validate estimated driving time is reasonable."""
        if value <= 0:
            raise serializers.ValidationError(
                "Estimated driving time must be greater than 0"
            )
        if value > 43200:  # 30 days in minutes - reasonable upper limit
            raise serializers.ValidationError(
                "Estimated driving time seems unreasonably large"
            )
        return value

    def validate(self, data):
        """Perform cross-field validation for route data."""
        distance = float(data.get("total_distance_miles", 0))
        time_minutes = data.get("estimated_driving_time_minutes", 0)

        if distance > 0 and time_minutes > 0:
            # Calculate average speed
            time_hours = time_minutes / 60
            avg_speed = distance / time_hours

            # Validate average speed is reasonable (5-85 mph for trucks)
            if avg_speed < 5:
                raise serializers.ValidationError(
                    f"Average speed {avg_speed:.1f} mph seems too low"
                )
            if avg_speed > 85:
                raise serializers.ValidationError(
                    f"Average speed {avg_speed:.1f} mph seems too high for commercial vehicles"
                )

        return data


class RouteStatsSerializer(serializers.Serializer):
    """
    Serializer for route statistics and summary information.

    Used for route analysis and summary displays without
    the full route details.
    """

    total_distance_miles = serializers.DecimalField(max_digits=8, decimal_places=2)
    estimated_driving_time_hours = serializers.DecimalField(
        max_digits=5, decimal_places=2
    )
    average_speed_mph = serializers.DecimalField(max_digits=4, decimal_places=1)
    waypoints_count = serializers.IntegerField()
    mandatory_stops_count = serializers.IntegerField()
    fuel_stops_count = serializers.IntegerField()
    total_time_with_stops_hours = serializers.DecimalField(
        max_digits=5, decimal_places=2
    )
    mapping_service = serializers.CharField()
    calculated_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")

    # HOS impact
    driving_days_required = serializers.SerializerMethodField()
    rest_periods_required = serializers.SerializerMethodField()

    def get_driving_days_required(self, obj):
        """Calculate how many driving days this route will require."""
        total_hours = float(obj.get("total_time_with_stops_hours", 0))
        # Assuming 11 hours max driving per day
        return int((total_hours / 11) + 0.999)  # Round up

    def get_rest_periods_required(self, obj):
        """Calculate number of rest periods required."""
        driving_days = self.get_driving_days_required(obj)
        return max(0, driving_days - 1)  # One less than driving days
