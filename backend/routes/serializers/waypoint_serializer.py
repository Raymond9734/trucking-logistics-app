"""
Waypoint serializers for routes app.

Contains serializers for Waypoint model including location information
and stop details for route planning.
"""

from rest_framework import serializers
from ..models import Waypoint


class WaypointSerializer(serializers.ModelSerializer):
    """
    Standard Waypoint serializer for waypoint information.

    Used for displaying waypoint details in route information
    and waypoint listings.
    """

    # Computed fields
    estimated_time_from_previous_hours = serializers.ReadOnlyField()
    estimated_stop_duration_hours = serializers.ReadOnlyField()
    coordinates = serializers.SerializerMethodField()

    # Display fields
    stop_type_display_name = serializers.ReadOnlyField()
    location_for_display = serializers.SerializerMethodField()

    class Meta:
        model = Waypoint
        fields = [
            "id",
            "sequence_order",
            "waypoint_type",
            "stop_type_display_name",
            "latitude",
            "longitude",
            "coordinates",
            "address",
            "distance_from_previous_miles",
            "estimated_time_from_previous_minutes",
            "estimated_time_from_previous_hours",
            "is_mandatory_stop",
            "estimated_stop_duration_minutes",
            "estimated_stop_duration_hours",
            "stop_reason",
            "hos_regulation",
            "location_for_display",
            "notes",
        ]
        read_only_fields = [
            "id",
            "estimated_time_from_previous_hours",
            "estimated_stop_duration_hours",
            "stop_type_display_name",
            "coordinates",
            "location_for_display",
        ]

    def get_coordinates(self, obj):
        """Get coordinates as a tuple."""
        return obj.get_coordinates()

    def get_location_for_display(self, obj):
        """Get formatted location for display."""
        if obj.address:
            return obj.address
        elif obj.latitude and obj.longitude:
            return f"{obj.latitude:.4f}, {obj.longitude:.4f}"
        else:
            return "Location not specified"


class WaypointCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating waypoints.

    Used by the route calculation service to create waypoints
    along calculated routes.
    """

    class Meta:
        model = Waypoint
        fields = [
            "route",
            "sequence_order",
            "waypoint_type",
            "latitude",
            "longitude",
            "address",
            "distance_from_previous_miles",
            "estimated_time_from_previous_minutes",
            "is_mandatory_stop",
            "estimated_stop_duration_minutes",
            "stop_reason",
            "hos_regulation",
            "notes",
        ]

    def validate_sequence_order(self, value):
        """Validate sequence order is non-negative."""
        if value < 0:
            raise serializers.ValidationError("Sequence order cannot be negative")
        return value

    def validate_latitude(self, value):
        """Validate latitude is within valid range."""
        if not (-90 <= float(value) <= 90):
            raise serializers.ValidationError(
                "Latitude must be between -90 and 90 degrees"
            )
        return value

    def validate_longitude(self, value):
        """Validate longitude is within valid range."""
        if not (-180 <= float(value) <= 180):
            raise serializers.ValidationError(
                "Longitude must be between -180 and 180 degrees"
            )
        return value

    def validate_distance_from_previous_miles(self, value):
        """Validate distance is non-negative."""
        if value < 0:
            raise serializers.ValidationError("Distance cannot be negative")
        return value

    def validate_estimated_time_from_previous_minutes(self, value):
        """Validate time is non-negative."""
        if value < 0:
            raise serializers.ValidationError("Time cannot be negative")
        return value

    def validate_estimated_stop_duration_minutes(self, value):
        """Validate stop duration is reasonable."""
        if value < 0:
            raise serializers.ValidationError("Stop duration cannot be negative")
        if value > 2040:  # 34 hours in minutes (max for 34-hour restart)
            raise serializers.ValidationError("Stop duration cannot exceed 34 hours")
        return value


class WaypointDetailSerializer(WaypointSerializer):
    """
    Detailed Waypoint serializer with additional calculated information.

    Includes cumulative distance and time calculations for comprehensive
    waypoint information in detailed route displays.
    """

    # Additional calculated fields
    cumulative_distance_miles = serializers.SerializerMethodField()
    cumulative_time_hours = serializers.SerializerMethodField()
    is_hos_required_stop = serializers.ReadOnlyField()
    is_trip_location = serializers.ReadOnlyField()

    class Meta(WaypointSerializer.Meta):
        fields = WaypointSerializer.Meta.fields + [
            "cumulative_distance_miles",
            "cumulative_time_hours",
            "is_hos_required_stop",
            "is_trip_location",
        ]

    def get_cumulative_distance_miles(self, obj):
        """Get cumulative distance from route start."""
        return obj.calculate_cumulative_distance_miles()

    def get_cumulative_time_hours(self, obj):
        """Get cumulative time from route start in hours."""
        minutes = obj.calculate_cumulative_time_minutes()
        return round(minutes / 60, 2)


class WaypointStopSerializer(serializers.Serializer):
    """
    Specialized serializer for stop information only.

    Used for displaying stop details in route summaries and
    HOS compliance information.
    """

    waypoint_type = serializers.CharField()
    stop_type_display_name = serializers.CharField()
    address = serializers.CharField()
    coordinates = serializers.ListField(
        child=serializers.DecimalField(max_digits=10, decimal_places=7)
    )
    is_mandatory_stop = serializers.BooleanField()
    estimated_stop_duration_hours = serializers.DecimalField(
        max_digits=4, decimal_places=2
    )
    stop_reason = serializers.CharField()
    hos_regulation = serializers.CharField()
    cumulative_distance_miles = serializers.DecimalField(max_digits=8, decimal_places=2)
    cumulative_time_hours = serializers.DecimalField(max_digits=5, decimal_places=2)


class WaypointSummarySerializer(serializers.Serializer):
    """
    Summary serializer for route waypoint statistics.

    Provides overview statistics about waypoints in a route
    without detailed individual waypoint information.
    """

    total_waypoints = serializers.IntegerField()
    mandatory_stops = serializers.IntegerField()
    optional_stops = serializers.IntegerField()
    fuel_stops = serializers.IntegerField()
    rest_stops = serializers.IntegerField()
    break_stops = serializers.IntegerField()

    # Stop duration summary
    total_stop_time_hours = serializers.DecimalField(max_digits=5, decimal_places=2)
    average_stop_duration_minutes = serializers.DecimalField(
        max_digits=4, decimal_places=1
    )

    # Distance summary
    total_route_distance_miles = serializers.DecimalField(
        max_digits=8, decimal_places=2
    )
    average_segment_distance_miles = serializers.DecimalField(
        max_digits=6, decimal_places=2
    )

    def to_representation(self, waypoints_queryset):
        """Convert waypoints queryset to summary statistics."""
        waypoints = waypoints_queryset.all()

        total_waypoints = len(waypoints)
        mandatory_stops = len([w for w in waypoints if w.is_mandatory_stop])
        optional_stops = total_waypoints - mandatory_stops

        # Count by type
        fuel_stops = len([w for w in waypoints if w.waypoint_type == "fuel_stop"])
        rest_stops = len([w for w in waypoints if w.waypoint_type == "rest_stop"])
        break_stops = len(
            [w for w in waypoints if w.waypoint_type in ["break_30min", "break_10hour"]]
        )

        # Calculate durations
        total_stop_time = sum(w.estimated_stop_duration_minutes for w in waypoints)
        total_stop_time_hours = total_stop_time / 60
        avg_stop_duration = (
            total_stop_time / total_waypoints if total_waypoints > 0 else 0
        )

        # Calculate distances
        total_distance = sum(float(w.distance_from_previous_miles) for w in waypoints)
        avg_segment_distance = (
            total_distance / total_waypoints if total_waypoints > 0 else 0
        )

        return {
            "total_waypoints": total_waypoints,
            "mandatory_stops": mandatory_stops,
            "optional_stops": optional_stops,
            "fuel_stops": fuel_stops,
            "rest_stops": rest_stops,
            "break_stops": break_stops,
            "total_stop_time_hours": round(total_stop_time_hours, 2),
            "average_stop_duration_minutes": round(avg_stop_duration, 1),
            "total_route_distance_miles": round(total_distance, 2),
            "average_segment_distance_miles": round(avg_segment_distance, 2),
        }
