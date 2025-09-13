"""
Log Sheet model for ELD compliance.

Contains the LogSheet model that represents the visual/formatted
version of daily logs for rendering and compliance validation.
"""

import uuid
from django.db import models
from django.utils import timezone


class LogSheet(models.Model):
    """
    Complete log sheet representation for rendering/printing.
    
    Contains all the visual/formatting information needed to generate
    a compliant daily log sheet that matches FMCSA requirements.
    This model handles the visual representation and compliance validation
    of the daily log data.
    
    Attributes:
        id: UUID primary key
        daily_log: One-to-one relationship with DailyLog
        grid_data: 24-hour grid data for visual representation
        has_graph_lines: Whether duty status lines have been drawn
        pdf_generated: Whether PDF version has been generated
        pdf_file_path: Path to generated PDF file
        is_compliant: Whether log sheet meets HOS requirements
        compliance_issues: List of compliance issues found
        generated_at: When log sheet was generated
        generator_version: Version of log generation system used
    """
    
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False,
        help_text="Unique identifier for the log sheet"
    )
    
    # Link to daily log (one-to-one relationship)
    daily_log = models.OneToOneField(
        'eld_logs.DailyLog',
        on_delete=models.CASCADE,
        related_name='log_sheet',
        help_text="The daily log this sheet represents"
    )
    
    # Grid representation (24-hour timeline)
    # Each hour is represented as a JSON object with duty status
    grid_data = models.JSONField(
        default=dict,
        help_text="24-hour grid data for visual representation"
    )
    
    # Generated visual elements
    has_graph_lines = models.BooleanField(
        default=False,
        help_text="Whether duty status lines have been drawn on grid"
    )
    
    # Export formats available
    pdf_generated = models.BooleanField(
        default=False,
        help_text="Whether PDF version has been generated"
    )
    
    pdf_file_path = models.CharField(
        max_length=500, 
        blank=True,
        help_text="Path to generated PDF file"
    )
    
    # Additional export formats
    image_generated = models.BooleanField(
        default=False,
        help_text="Whether image version has been generated"
    )
    
    image_file_path = models.CharField(
        max_length=500,
        blank=True, 
        help_text="Path to generated image file"
    )
    
    # Compliance validation
    is_compliant = models.BooleanField(
        default=True,
        help_text="Whether this log sheet meets HOS requirements"
    )
    
    compliance_issues = models.JSONField(
        default=list,
        help_text="List of compliance issues found"
    )
    
    # Compliance check details
    last_compliance_check = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When compliance was last checked"
    )
    
    compliance_score = models.PositiveIntegerField(
        default=100,
        help_text="Compliance score (0-100)"
    )
    
    # Generation metadata
    generated_at = models.DateTimeField(
        auto_now=True,
        help_text="When log sheet was last generated"
    )
    
    generator_version = models.CharField(
        max_length=50,
        default="1.0",
        help_text="Version of log generation system used"
    )
    
    # Layout and formatting options
    class LayoutSize(models.TextChoices):
        LETTER = 'letter', 'Letter (8.5" x 11")'
        LEGAL = 'legal', 'Legal (8.5" x 14")'
        A4 = 'a4', 'A4 (210mm x 297mm)'
    
    layout_size = models.CharField(
        max_length=10,
        choices=LayoutSize.choices,
        default=LayoutSize.LETTER,
        help_text="Page size for generated documents"
    )
    
    # Theme/style options
    class ColorTheme(models.TextChoices):
        STANDARD = 'standard', 'Standard Black/White'
        COLOR = 'color', 'Color-Coded Status'
        HIGH_CONTRAST = 'high_contrast', 'High Contrast'
    
    color_theme = models.CharField(
        max_length=15,
        choices=ColorTheme.choices,
        default=ColorTheme.STANDARD,
        help_text="Color theme for visual representation"
    )
    
    class Meta:
        db_table = 'eld_logs_logsheet'
        verbose_name = 'Log Sheet'
        verbose_name_plural = 'Log Sheets'
        indexes = [
            models.Index(fields=['daily_log']),
            models.Index(fields=['is_compliant']),
            models.Index(fields=['generated_at']),
        ]
    
    def __str__(self):
        """Return string representation of the log sheet."""
        return f"Log Sheet for {self.daily_log.log_date} - {self.daily_log.driver_name}"
    
    def generate_grid_data(self):
        """Generate 24-hour grid data from duty status records."""
        
        # Initialize 24-hour grid (0-23 hours)
        grid = {}
        for hour in range(24):
            grid[str(hour)] = {
                'duty_status': 'off_duty',
                'location': '',
                'remarks': '',
                'minutes': {str(minute): 'off_duty' for minute in range(60)}  # 15-minute intervals
            }
        
        # Fill grid with duty status records
        records = self.daily_log.duty_status_records.all().order_by('sequence_order')
        
        for record in records:
            start_hour = record.start_time.hour
            start_minute = record.start_time.minute
            duration_minutes = record.duration_minutes
            
            # Fill the grid for this duty status period
            current_time = record.start_time
            remaining_minutes = duration_minutes
            
            while remaining_minutes > 0 and current_time.hour < 24:
                hour_str = str(current_time.hour)
                
                # Update hour-level data
                grid[hour_str]['duty_status'] = record.duty_status
                grid[hour_str]['location'] = record.location_for_remarks
                grid[hour_str]['remarks'] = record.remarks
                
                # Update minute-level data for more precise representation
                minutes_in_hour = min(60 - current_time.minute, remaining_minutes)
                for minute_offset in range(minutes_in_hour):
                    minute = current_time.minute + minute_offset
                    if minute < 60:
                        grid[hour_str]['minutes'][str(minute)] = record.duty_status
                
                # Move to next hour
                remaining_minutes -= minutes_in_hour
                if remaining_minutes > 0:
                    current_time = current_time.replace(hour=current_time.hour + 1, minute=0)
        
        self.grid_data = grid
        self.has_graph_lines = True
        self.save()
    
    def validate_compliance(self):
        """Validate log sheet against HOS regulations."""
        
        issues = []
        
        # Get daily log for validation
        daily_log = self.daily_log
        
        # Check total hours add up to 24
        total_hours = float(daily_log.total_hours_sum)
        if abs(total_hours - 24.0) > 0.1:  # Allow small rounding differences
            issues.append({
                'type': 'incomplete_hours',
                'severity': 'error',
                'description': f"Total hours ({total_hours}) does not equal 24",
                'regulation': '395.8(a)'
            })
        
        # Check driving time limit (11 hours)
        if daily_log.total_hours_driving > 11:
            issues.append({
                'type': 'driving_limit_exceeded',
                'severity': 'violation',
                'description': f"Driving time ({daily_log.total_hours_driving}h) exceeds 11-hour limit",
                'regulation': '395.3(a)(3)'
            })
        
        # Check for required location information
        records_without_location = daily_log.duty_status_records.filter(
            location_city='',
            location_state='',
            location_description=''
        )
        
        if records_without_location.exists():
            issues.append({
                'type': 'missing_location',
                'severity': 'warning',
                'description': f"{records_without_location.count()} duty status changes missing location information",
                'regulation': '395.8(a)'
            })
        
        # Check for 30-minute break requirement
        driving_records = daily_log.duty_status_records.filter(
            duty_status='driving'
        ).order_by('sequence_order')
        
        continuous_driving_minutes = 0
        found_break_violation = False
        
        for record in driving_records:
            continuous_driving_minutes += record.duration_minutes
            
            if continuous_driving_minutes > 480:  # 8 hours = 480 minutes
                # Look for 30-minute break after this point
                next_records = daily_log.duty_status_records.filter(
                    sequence_order__gt=record.sequence_order
                ).order_by('sequence_order')
                
                found_break = False
                for next_record in next_records:
                    if next_record.duty_status != 'driving':
                        if next_record.duration_minutes >= 30:
                            found_break = True
                            continuous_driving_minutes = 0
                            break
                        elif next_record.duty_status == 'driving':
                            break
                
                if not found_break and continuous_driving_minutes > 480:
                    found_break_violation = True
                    break
        
        if found_break_violation:
            issues.append({
                'type': 'missing_30min_break',
                'severity': 'violation',
                'description': "30-minute break required after 8 hours of driving",
                'regulation': '395.3(a)(3)(ii)'
            })
        
        # Check for driver certification
        if not daily_log.is_certified:
            issues.append({
                'type': 'not_certified',
                'severity': 'warning',
                'description': "Log has not been certified by driver",
                'regulation': '395.8(e)(2)'
            })
        
        # Calculate compliance score
        error_count = len([issue for issue in issues if issue['severity'] == 'error'])
        violation_count = len([issue for issue in issues if issue['severity'] == 'violation'])
        warning_count = len([issue for issue in issues if issue['severity'] == 'warning'])
        
        # Score calculation: start at 100, subtract points for issues
        score = 100
        score -= error_count * 25      # Errors: -25 points each
        score -= violation_count * 15  # Violations: -15 points each
        score -= warning_count * 5     # Warnings: -5 points each
        
        self.compliance_issues = issues
        self.is_compliant = len([issue for issue in issues if issue['severity'] in ['error', 'violation']]) == 0
        self.compliance_score = max(0, score)
        self.last_compliance_check = timezone.now()
        self.save()
        
        return {
            'is_compliant': self.is_compliant,
            'compliance_score': self.compliance_score,
            'issues': issues,
            'summary': {
                'total_issues': len(issues),
                'errors': error_count,
                'violations': violation_count,
                'warnings': warning_count
            }
        }
    
    def get_visual_grid_html(self):
        """Generate HTML representation of the 24-hour grid."""
        if not self.grid_data:
            self.generate_grid_data()
        
        # This would generate HTML for the visual grid
        # Implementation would create the actual log sheet visual
        return "<div class='eld-log-grid'>Grid visualization would go here</div>"
    
    def get_export_formats(self):
        """Get available export formats."""
        formats = []
        
        if self.pdf_generated and self.pdf_file_path:
            formats.append({
                'type': 'pdf',
                'path': self.pdf_file_path,
                'available': True
            })
        
        if self.image_generated and self.image_file_path:
            formats.append({
                'type': 'image',
                'path': self.image_file_path,
                'available': True
            })
        
        # Always available formats
        formats.extend([
            {'type': 'json', 'available': True},
            {'type': 'html', 'available': True}
        ])
        
        return formats
    
    def get_generation_status(self):
        """Get status of log sheet generation."""
        return {
            'has_grid_data': bool(self.grid_data),
            'has_graph_lines': self.has_graph_lines,
            'pdf_generated': self.pdf_generated,
            'image_generated': self.image_generated,
            'generated_at': self.generated_at.isoformat(),
            'generator_version': self.generator_version,
            'compliance_checked': self.last_compliance_check is not None,
            'is_compliant': self.is_compliant,
            'compliance_score': self.compliance_score
        }
