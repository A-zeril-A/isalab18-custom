from odoo import http
from odoo.http import content_disposition, request
import base64
import logging

_logger = logging.getLogger(__name__)


class TimesheetReportController(http.Controller):
    """Controller for handling timesheet report file downloads"""

    @http.route('/timesheet/export/xml', type='http', auth="user", methods=['GET', 'POST'])
    def export_timesheet_xml(self, data=None, filename=None, **kwargs):
        """
        Download XML file for timesheet report.
        
        Args:
            data: Base64 encoded XML content
            filename: Name for the downloaded file
            
        Returns:
            HTTP response with XML file download
        """
        if not data or not filename:
            return request.not_found("Missing required parameters: data and filename")
        
        try:
            file_content = base64.b64decode(data)
            return request.make_response(
                file_content,
                headers=[
                    ('Content-Type', 'application/xml; charset=utf-8'),
                    ('Content-Disposition', content_disposition(filename)),
                    ('Content-Length', len(file_content)),
                ]
            )
        except base64.binascii.Error as e:
            _logger.error(f"Failed to decode base64 data: {e}")
            return request.not_found("Invalid file data encoding")
        except Exception as e:
            _logger.error(f"Error generating XML file: {e}")
            return request.not_found(f"Error generating file: {str(e)}")
