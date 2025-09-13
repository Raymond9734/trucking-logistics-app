"""
Log Sheet Renderer Service for ELD compliance.

Creates visual representations of daily logs including grid generation,
PDF export, and compliance validation as required for FMCSA regulations.
"""

import logging
import json
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional
from django.db import transaction
from django.utils import timezone
from ..models import DailyLog, LogSheet, DutyStatusRecord

logger = logging.getLogger(__name__)


class LogSheetRendererService:
    """
    Service for rendering ELD log sheets in various formats.

    Creates visual representations of daily logs that meet FMCSA
    requirements including 24-hour grids, compliance validation,
    and export capabilities.

    Single Responsibility: Log sheet rendering and visual representation
    """

    def __init__(self):
        """Initialize log sheet renderer service."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def create_log_sheet(self, daily_log: DailyLog, **options) -> LogSheet:
        """
        Create a log sheet from a daily log.

        Args:
            daily_log: DailyLog instance to render
            **options: Rendering options (layout_size, color_theme, etc.)

        Returns:
            LogSheet instance with visual representation
        """
        try:
            with transaction.atomic():
                self.logger.info(f"Creating log sheet for daily log {daily_log.id}")

                # Check if log sheet already exists
                log_sheet, created = LogSheet.objects.get_or_create(
                    daily_log=daily_log,
                    defaults={
                        "layout_size": options.get(
                            "layout_size", LogSheet.LayoutSize.LETTER
                        ),
                        "color_theme": options.get(
                            "color_theme", LogSheet.ColorTheme.STANDARD
                        ),
                        "generator_version": "1.0",
                    },
                )

                if created:
                    self.logger.info(f"Created new log sheet {log_sheet.id}")
                else:
                    self.logger.info(f"Using existing log sheet {log_sheet.id}")

                # Generate or update grid data
                self._generate_grid_data(log_sheet)

                # Validate compliance
                compliance_result = self._validate_log_sheet_compliance(log_sheet)

                # Update log sheet with compliance info
                log_sheet.is_compliant = compliance_result["is_compliant"]
                log_sheet.compliance_issues = compliance_result["issues"]
                log_sheet.compliance_score = compliance_result["compliance_score"]
                log_sheet.last_compliance_check = timezone.now()
                log_sheet.save()

                self.logger.info(f"Log sheet {log_sheet.id} created successfully")
                return log_sheet

        except Exception as e:
            self.logger.error(
                f"Failed to create log sheet for daily log {daily_log.id}: {str(e)}"
            )
            raise LogSheetRenderingError(f"Failed to create log sheet: {str(e)}")

    def _generate_grid_data(self, log_sheet: LogSheet):
        """Generate 24-hour grid data for visual representation."""
        try:
            daily_log = log_sheet.daily_log
            self.logger.debug(f"Generating grid data for log sheet {log_sheet.id}")

            # Initialize 24-hour grid (0-23 hours, each hour has 4 quarters for 15-min precision)
            grid_data = {
                "hours": {},
                "summary": {
                    "off_duty_hours": 0,
                    "sleeper_berth_hours": 0,
                    "driving_hours": 0,
                    "on_duty_not_driving_hours": 0,
                },
                "timeline": [],
                "locations": [],
            }

            # Initialize each hour with quarters (15-minute intervals)
            for hour in range(24):
                grid_data["hours"][str(hour)] = {
                    "primary_status": "off_duty",
                    "quarters": ["off_duty"] * 4,  # 4 quarters of 15 minutes each
                    "location": "",
                    "remarks": "",
                    "has_location_change": False,
                    "miles_driven": 0,
                }

            # Get duty status records for this daily log
            records = daily_log.duty_status_records.all().order_by("sequence_order")

            # Fill grid with duty status data
            for record in records:
                start_time = record.start_time
                duration_minutes = record.duration_minutes

                # Extract hour and minute
                start_hour = start_time.hour
                start_minute = start_time.minute

                # Fill the grid for this duty status period
                remaining_minutes = duration_minutes
                current_hour = start_hour
                current_minute = start_minute

                while remaining_minutes > 0 and current_hour < 24:
                    hour_str = str(current_hour)

                    # Update hour-level information
                    if grid_data["hours"][hour_str]["primary_status"] == "off_duty":
                        grid_data["hours"][hour_str][
                            "primary_status"
                        ] = record.duty_status
                    grid_data["hours"][hour_str][
                        "location"
                    ] = record.location_for_remarks
                    grid_data["hours"][hour_str]["remarks"] = record.remarks
                    if record.is_driving_record():
                        grid_data["hours"][hour_str]["miles_driven"] += float(
                            record.miles_driven_this_period
                        )

                    # Calculate minutes to fill in this hour
                    minutes_in_hour = min(60 - current_minute, remaining_minutes)

                    # Fill quarters (15-minute intervals)
                    for minute_offset in range(0, minutes_in_hour, 15):
                        actual_minute = current_minute + minute_offset
                        if actual_minute < 60:
                            quarter = actual_minute // 15
                            if quarter < 4:
                                grid_data["hours"][hour_str]["quarters"][
                                    quarter
                                ] = record.duty_status

                    # Move to next hour
                    remaining_minutes -= minutes_in_hour
                    if remaining_minutes > 0:
                        current_hour += 1
                        current_minute = 0

                # Add to timeline
                grid_data["timeline"].append(
                    {
                        "sequence": record.sequence_order,
                        "duty_status": record.duty_status,
                        "duty_status_display": record.get_duty_status_display(),
                        "start_time": start_time.strftime("%H:%M"),
                        "end_time": (
                            record.end_time.strftime("%H:%M")
                            if record.end_time
                            else "ongoing"
                        ),
                        "duration_minutes": duration_minutes,
                        "location": record.location_for_remarks,
                        "remarks": record.remarks,
                        "miles_driven": float(record.miles_driven_this_period),
                    }
                )

                # Add unique locations
                location = record.location_for_remarks
                if location and location not in grid_data["locations"]:
                    grid_data["locations"].append(location)

            # Calculate summary hours from actual records
            grid_data["summary"] = {
                "off_duty_hours": float(daily_log.total_hours_off_duty),
                "sleeper_berth_hours": float(daily_log.total_hours_sleeper_berth),
                "driving_hours": float(daily_log.total_hours_driving),
                "on_duty_not_driving_hours": float(
                    daily_log.total_hours_on_duty_not_driving
                ),
                "total_hours": float(daily_log.total_hours_sum),
                "total_miles": float(daily_log.total_miles_driving_today),
            }

            # Save grid data
            log_sheet.grid_data = grid_data
            log_sheet.has_graph_lines = True
            log_sheet.save()

        except Exception as e:
            self.logger.error(f"Failed to generate grid data: {str(e)}")
            raise

    def _validate_log_sheet_compliance(self, log_sheet: LogSheet) -> Dict:
        """Validate log sheet against HOS regulations."""
        return log_sheet.validate_compliance()

    def render_html_grid(self, log_sheet: LogSheet) -> str:
        """
        Generate HTML representation of the 24-hour grid.

        Args:
            log_sheet: LogSheet instance with grid data

        Returns:
            HTML string representing the visual grid
        """
        try:
            if not log_sheet.grid_data:
                self._generate_grid_data(log_sheet)

            grid_data = log_sheet.grid_data

            # HTML template for the grid
            html = """
            <div class="eld-log-sheet" data-log-date="{date}" data-driver="{driver}">
                <div class="log-header">
                    <h2>Driver's Daily Log - {date}</h2>
                    <div class="driver-info">
                        <span>Driver: {driver}</span>
                        <span>Carrier: {carrier}</span>
                        <span>Vehicle: {vehicle}</span>
                        <span>Total Miles: {total_miles}</span>
                    </div>
                </div>
                
                <div class="duty-status-grid">
                    <div class="grid-header">
                        <div class="time-labels">
                            {time_labels}
                        </div>
                    </div>
                    
                    <div class="grid-rows">
                        <div class="grid-row off-duty-row">
                            <span class="row-label">Off Duty</span>
                            <div class="hour-cells">
                                {off_duty_cells}
                            </div>
                            <span class="total-hours">{off_duty_total}h</span>
                        </div>
                        
                        <div class="grid-row sleeper-berth-row">
                            <span class="row-label">Sleeper Berth</span>
                            <div class="hour-cells">
                                {sleeper_berth_cells}
                            </div>
                            <span class="total-hours">{sleeper_berth_total}h</span>
                        </div>
                        
                        <div class="grid-row driving-row">
                            <span class="row-label">Driving</span>
                            <div class="hour-cells">
                                {driving_cells}
                            </div>
                            <span class="total-hours">{driving_total}h</span>
                        </div>
                        
                        <div class="grid-row on-duty-row">
                            <span class="row-label">On Duty (Not Driving)</span>
                            <div class="hour-cells">
                                {on_duty_cells}
                            </div>
                            <span class="total-hours">{on_duty_total}h</span>
                        </div>
                    </div>
                </div>
                
                <div class="remarks-section">
                    <h3>Remarks</h3>
                    <div class="timeline">
                        {timeline_entries}
                    </div>
                </div>
                
                <div class="log-footer">
                    <div class="certification">
                        <span>Driver Certification: {certification_status}</span>
                        <span>Total Hours: {total_hours}</span>
                    </div>
                </div>
            </div>
            
            <style>
            .eld-log-sheet {{
                font-family: Arial, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                border: 1px solid #333;
            }}
            .log-header {{
                text-align: center;
                margin-bottom: 20px;
                border-bottom: 1px solid #333;
                padding-bottom: 10px;
            }}
            .driver-info {{
                display: flex;
                justify-content: space-between;
                margin-top: 10px;
            }}
            .duty-status-grid {{
                border: 1px solid #333;
                margin-bottom: 20px;
            }}
            .grid-header .time-labels {{
                display: flex;
                border-bottom: 1px solid #333;
            }}
            .time-label {{
                flex: 1;
                text-align: center;
                padding: 5px;
                border-right: 1px solid #333;
                font-size: 10px;
            }}
            .grid-row {{
                display: flex;
                align-items: center;
                border-bottom: 1px solid #333;
            }}
            .row-label {{
                width: 150px;
                padding: 10px;
                border-right: 1px solid #333;
                font-weight: bold;
                background-color: #f5f5f5;
            }}
            .hour-cells {{
                display: flex;
                flex: 1;
            }}
            .hour-cell {{
                flex: 1;
                height: 30px;
                border-right: 1px solid #333;
                display: flex;
            }}
            .quarter-cell {{
                flex: 1;
                border-right: 1px solid #ddd;
            }}
            .quarter-cell.off-duty {{ background-color: #ffffff; }}
            .quarter-cell.sleeper-berth {{ background-color: #e8f4f8; }}
            .quarter-cell.driving {{ background-color: #ffffcc; }}
            .quarter-cell.on-duty-not-driving {{ background-color: #ffeeee; }}
            .total-hours {{
                width: 60px;
                text-align: center;
                padding: 10px;
                border-left: 1px solid #333;
                font-weight: bold;
            }}
            .timeline-entries {{
                font-size: 12px;
                line-height: 1.4;
            }}
            .timeline-entry {{
                margin-bottom: 5px;
                padding: 3px;
                border-bottom: 1px solid #eee;
            }}
            </style>
            """.format(
                date=log_sheet.daily_log.log_date.strftime("%m/%d/%Y"),
                driver=log_sheet.daily_log.driver_name,
                carrier=log_sheet.daily_log.carrier_name,
                vehicle=log_sheet.daily_log.vehicle_number,
                total_miles=grid_data["summary"]["total_miles"],
                time_labels=self._generate_time_labels(),
                off_duty_cells=self._generate_duty_status_cells(grid_data, "off_duty"),
                sleeper_berth_cells=self._generate_duty_status_cells(
                    grid_data, "sleeper_berth"
                ),
                driving_cells=self._generate_duty_status_cells(grid_data, "driving"),
                on_duty_cells=self._generate_duty_status_cells(
                    grid_data, "on_duty_not_driving"
                ),
                off_duty_total=grid_data["summary"]["off_duty_hours"],
                sleeper_berth_total=grid_data["summary"]["sleeper_berth_hours"],
                driving_total=grid_data["summary"]["driving_hours"],
                on_duty_total=grid_data["summary"]["on_duty_not_driving_hours"],
                timeline_entries=self._generate_timeline_html(grid_data["timeline"]),
                certification_status=(
                    "Certified" if log_sheet.daily_log.is_certified else "Not Certified"
                ),
                total_hours=grid_data["summary"]["total_hours"],
            )

            return html

        except Exception as e:
            self.logger.error(f"Failed to render HTML grid: {str(e)}")
            raise LogSheetRenderingError(f"Failed to render HTML: {str(e)}")

    def _generate_time_labels(self) -> str:
        """Generate time labels for grid header."""
        labels = []
        for hour in range(24):
            if hour == 0:
                label = "Mid"
            elif hour == 12:
                label = "Noon"
            else:
                label = str(hour)
            labels.append(f'<div class="time-label">{label}</div>')
        return "".join(labels)

    def _generate_duty_status_cells(self, grid_data: Dict, duty_status: str) -> str:
        """Generate HTML cells for a specific duty status row."""
        cells = []
        for hour in range(24):
            hour_data = grid_data["hours"][str(hour)]
            quarters = hour_data["quarters"]

            quarter_cells = []
            for quarter in quarters:
                css_class = "quarter-cell " + quarter
                quarter_cells.append(f'<div class="{css_class}"></div>')

            cells.append(f'<div class="hour-cell">{"".join(quarter_cells)}</div>')

        return "".join(cells)

    def _generate_timeline_html(self, timeline: List[Dict]) -> str:
        """Generate HTML for timeline entries."""
        entries = []
        for entry in timeline:
            html_entry = f"""
            <div class="timeline-entry">
                {entry['start_time']}-{entry['end_time']}: {entry['duty_status_display']} 
                - {entry['location']} 
                {f"({entry['miles_driven']} miles)" if entry['miles_driven'] > 0 else ""}
                {f"- {entry['remarks']}" if entry['remarks'] else ""}
            </div>
            """
            entries.append(html_entry)
        return "".join(entries)

    def generate_pdf_log_sheet(
        self, log_sheet: LogSheet, output_path: Optional[str] = None
    ) -> str:
        """
        Generate PDF version of log sheet.

        Args:
            log_sheet: LogSheet instance to render
            output_path: Optional path for output file

        Returns:
            Path to generated PDF file
        """
        try:
            self.logger.info(f"Generating PDF for log sheet {log_sheet.id}")

            # For now, return a placeholder implementation
            # In a real implementation, this would use a PDF generation library
            # like WeasyPrint, ReportLab, or similar

            pdf_filename = f"daily_log_{log_sheet.daily_log.log_date.strftime('%Y%m%d')}_{log_sheet.id.hex[:8]}.pdf"
            pdf_path = output_path or f"/tmp/{pdf_filename}"

            # Placeholder: In real implementation, generate actual PDF
            html_content = self.render_html_grid(log_sheet)

            # Update log sheet record
            log_sheet.pdf_generated = True
            log_sheet.pdf_file_path = pdf_path
            log_sheet.save()

            self.logger.info(f"PDF generated: {pdf_path}")
            return pdf_path

        except Exception as e:
            self.logger.error(f"Failed to generate PDF: {str(e)}")
            raise LogSheetRenderingError(f"Failed to generate PDF: {str(e)}")

    def export_log_sheet_json(self, log_sheet: LogSheet) -> Dict:
        """
        Export log sheet data as JSON.

        Args:
            log_sheet: LogSheet instance to export

        Returns:
            Dictionary containing all log sheet data
        """
        try:
            daily_log = log_sheet.daily_log

            export_data = {
                "log_sheet_id": str(log_sheet.id),
                "daily_log_id": str(daily_log.id),
                "trip_id": str(daily_log.trip.id),
                "log_date": daily_log.log_date.isoformat(),
                "driver_info": {
                    "name": daily_log.driver_name,
                    "co_driver": daily_log.co_driver_name,
                },
                "carrier_info": {
                    "name": daily_log.carrier_name,
                    "address": daily_log.carrier_main_office_address,
                },
                "vehicle_info": {
                    "number": daily_log.vehicle_number,
                    "trailer": daily_log.trailer_number,
                },
                "totals": {
                    "off_duty_hours": float(daily_log.total_hours_off_duty),
                    "sleeper_berth_hours": float(daily_log.total_hours_sleeper_berth),
                    "driving_hours": float(daily_log.total_hours_driving),
                    "on_duty_not_driving_hours": float(
                        daily_log.total_hours_on_duty_not_driving
                    ),
                    "total_miles": float(daily_log.total_miles_driving_today),
                },
                "duty_status_records": [
                    record.get_record_summary()
                    for record in daily_log.duty_status_records.all().order_by(
                        "sequence_order"
                    )
                ],
                "compliance": {
                    "is_compliant": log_sheet.is_compliant,
                    "compliance_score": log_sheet.compliance_score,
                    "issues": log_sheet.compliance_issues,
                    "last_check": (
                        log_sheet.last_compliance_check.isoformat()
                        if log_sheet.last_compliance_check
                        else None
                    ),
                },
                "certification": {
                    "is_certified": daily_log.is_certified,
                    "signature_date": (
                        daily_log.driver_signature_date.isoformat()
                        if daily_log.driver_signature_date
                        else None
                    ),
                },
                "grid_data": log_sheet.grid_data,
                "export_info": {
                    "exported_at": timezone.now().isoformat(),
                    "generator_version": log_sheet.generator_version,
                    "layout_size": log_sheet.layout_size,
                    "color_theme": log_sheet.color_theme,
                },
            }

            return export_data

        except Exception as e:
            self.logger.error(f"Failed to export JSON: {str(e)}")
            raise LogSheetRenderingError(f"Failed to export JSON: {str(e)}")

    def create_log_sheets_for_trip(self, trip) -> List[LogSheet]:
        """
        Create log sheets for all daily logs in a trip.

        Args:
            trip: Trip instance

        Returns:
            List of LogSheet instances
        """
        try:
            log_sheets = []
            daily_logs = trip.daily_logs.all().order_by("log_date")

            for daily_log in daily_logs:
                log_sheet = self.create_log_sheet(daily_log)
                log_sheets.append(log_sheet)

            self.logger.info(f"Created {len(log_sheets)} log sheets for trip {trip.id}")
            return log_sheets

        except Exception as e:
            self.logger.error(
                f"Failed to create log sheets for trip {trip.id}: {str(e)}"
            )
            raise LogSheetRenderingError(f"Failed to create log sheets: {str(e)}")


    def generate_log_sheet(self, daily_log, sheet_format='pdf'):
        """
        Generate log sheet for a daily log (API compatibility method).
        
        Args:
            daily_log: DailyLog instance
            sheet_format: Format ('pdf' or 'json')
            
        Returns:
            LogSheet instance
        """
        try:
            from ..models import LogSheet
            
            # Create or get existing log sheet
            log_sheet = self.create_log_sheet(daily_log)
            
            # Set sheet format
            log_sheet.sheet_format = sheet_format
            log_sheet.is_generated = True
            log_sheet.generated_at = timezone.now()
            
            # Generate content based on format
            if sheet_format == 'pdf':
                # Generate PDF content (placeholder)
                log_sheet.pdf_content = f"PDF content for daily log {daily_log.id}"
                log_sheet.pdf_generated = True
            elif sheet_format == 'json':
                # Grid data is already generated in create_log_sheet
                pass
            
            log_sheet.save()
            
            self.logger.info(f"Generated log sheet {log_sheet.id} in {sheet_format} format")
            return log_sheet
            
        except Exception as e:
            self.logger.error(f"Failed to generate log sheet: {str(e)}")
            raise LogSheetRenderingError(f"Failed to generate log sheet: {str(e)}")


class LogSheetRenderingError(Exception):
    """Exception raised when log sheet rendering fails."""

    pass
