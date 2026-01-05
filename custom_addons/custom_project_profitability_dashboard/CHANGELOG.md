# Changelog

All notable changes to this project will be documented in this file.

## [18.0.1.0.0] - 2026-01-05

### Added
- Full Odoo 18 compatibility
- OWL 3 templates for project right side panel customization
- Contract Terms section showing allocated hours
- Project's Time Performance section with Effective/Remaining hours
- Project Financial Performance section with custom styling
- JavaScript patch for ProjectRightSidePanel component
- SCSS styles with dark mode support
- Financial Performance tab in project form view

### Changed
- Updated from Odoo 15 to Odoo 18 architecture
- Migrated from OWL 1 to OWL 3 template syntax
- Updated `timesheet_cost` field references to `hourly_cost` (Odoo 16+ change)
- Updated stat buttons to use `sequence` instead of `order`
- Updated profitability_items structure to use revenues/costs format
- Improved batch creation for report lines (performance optimization)

### Fixed
- Template inheritance for Odoo 18 OWL components
- Assets registration in manifest for web.assets_backend
- Security group comments and descriptions

### Technical Notes
- Uses `t-inherit-mode="extension"` for OWL template inheritance
- Compatible with sale_project, sale_timesheet, hr_timesheet modules
- Requires custom_business_trip_management module for travel costs

## [1.2.0] - Previous (Odoo 15)

### Features
- HR Team Cost Calculation per project
- Facilities costs (15% of HR costs)
- Travel & Lodging integration with business trips
- Custom security groups for financial data access
- Project Updates renamed to "Contract Performance Sheet"
- Profitability dashboard with margin analysis
