{
    'name': 'Employee Timesheet Report',
    'version': '18.0.1.1.0',
    'category': 'Human Resources/Timesheets',
    'summary': 'Advanced timesheet report with overtime, delay tracking and XML export',
    'description': """
Employee Timesheet Report
=========================

This module provides:
- Comprehensive timesheet reporting with start/end time tracking
- Office hours calculation (8:30-18:30 local time)
- Overtime calculation (18:00-22:00)
- Night overtime calculation (22:00-06:00)
- Delay/lateness tracking
- Weekend and Italian public holiday detection
- XML export for Italian payroll systems
- Leave records integration

Configuration:
- Add payroll_code to employees for proper XML export
- Server timezone should be set correctly for accurate hour calculations
    """,
    'author': 'Sajjad',
    'website': '',
    'license': 'LGPL-3',
    'depends': [
        'hr_timesheet',
        'hr_holidays',
        'project',
        'web',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/timesheet_report_views.xml',
        'views/hr_employee_views.xml',
    ],
    'assets': {},
    'installable': True,
    'application': False,
    'auto_install': False,
}
