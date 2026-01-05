# Custom Project Profitability Dashboard

**Version:** 18.0.1.0.0  
**Author:** A_zeril_A  
**License:** LGPL-3  

## Overview

This module extends the official Odoo Project module by adding a comprehensive profitability dashboard. It integrates HR team cost calculation, facilities costs, taxes, and other financial KPIs directly into the project interface.

## Key Features

### Financial Performance Dashboard
- **Untaxed Amount:** Total revenue from linked sale orders
- **HR Costs:** Automatically calculated from timesheet data and employee hourly rates
- **Facilities Costs:** Calculated as 15% of HR costs
- **Travel & Lodging:** Integrated with Business Trip Management module
- **Other Costs:** Custom costs from sale orders
- **Margin:** Net profit/loss calculation
- **Taxes:** Total taxes from sale orders

### Contract Terms Section
- **Allocated Hours:** Total hours allocated to the project
- **Displayed in:** Project right side panel

### Project's Time Performance
- **Effective Hours:** Actual hours worked (from timesheets)
- **Remaining Hours:** Allocated - Effective (with color coding)
- **Displayed in:** Project right side panel

### Security
- Custom security group: `Custom Profitability Access`
- Restricts access to sensitive financial data
- Integrates with analytic accounting group

### UI Enhancements
- Project Updates renamed to "Contract Performance Sheet"
- Custom styling for financial data (color-coded margins)
- Dark mode support
- HR Cost Alert warnings for employees without hourly rates

## Installation

1. Copy this module to your `custom_addons` directory
2. Update the app list: `Settings > Apps > Update Apps List`
3. Install the module: `Settings > Apps > Search "custom.project.profitability.dashboard"`

## Dependencies

- `base`
- `project`
- `sale`
- `sale_project`
- `sale_timesheet`
- `hr_timesheet`
- `analytic`
- `account`
- `custom_business_trip_management` (optional - for travel costs)

## Configuration

1. **Security Group:**
   - Navigate to `Settings > Users & Companies > Groups`
   - Add users to "Custom Profitability Access" group
   - Users need this group to view financial data

2. **Employee Hourly Rates:**
   - Navigate to `Employees > Employees`
   - Set the "Hourly Cost" field for each employee
   - Missing rates will trigger warning alerts

## Technical Details

### Odoo 18 Compatibility
- Uses OWL 3 template syntax
- Patches `ProjectRightSidePanel` component
- Uses `sequence` for button ordering
- Uses `revenues/costs` format for profitability items

### Computed Fields (Stored)
- `x_net_value`: Untaxed amount from sale orders
- `x_total_hr_cost`: Total HR costs from timesheets
- `x_facilities_cost`: 15% of HR costs
- `x_travel_lodging`: Business trip costs
- `x_other_costs`: Custom costs from sale orders
- `x_final_margin`: Net margin calculation
- `x_total_taxes`: Total taxes from sale orders
- `x_hr_cost_warning`: Warning for employees without rates

### Files Structure
```
custom_project_profitability_dashboard/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── project.py
│   └── custom_project_profitability_dashboard.py
├── views/
│   ├── custom_project_kanban_button_rename_inherit.xml
│   ├── custom_project_update_view_rename_inherit.xml
│   └── custom_project_profitability_dashboard_views.xml
├── security/
│   ├── groups.xml
│   ├── ir.model.access.csv
│   └── project_update_access.xml
├── static/
│   └── src/
│       ├── js/
│       │   └── project_right_side_panel.js
│       ├── xml/
│       │   └── project_profitability_override.xml
│       └── scss/
│           └── profitability_dashboard.scss
├── demo/
│   └── demo.xml
├── CHANGELOG.md
└── README.md
```

## Troubleshooting

### Financial data not showing
1. Ensure user has "Custom Profitability Access" group
2. Check that project has linked sale orders
3. Verify employees have timesheets with hourly rates

### HR Costs showing 0
1. Check employee "Hourly Cost" field is set
2. Verify timesheets are linked to the project
3. Look for HR Cost Alert warning

### Template errors
1. Clear browser cache
2. Restart Odoo server with `-u custom_project_profitability_dashboard`
3. Check browser console for JavaScript errors

## Support

For issues or feature requests, please contact the module author.
