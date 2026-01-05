from odoo import models, fields, api
from datetime import datetime, time, timedelta
import requests
import base64
import xml.etree.ElementTree as ET
import logging

_logger = logging.getLogger(__name__)


class HrEmployeeInherit(models.Model):
    """Add payroll code field to employee model"""
    _inherit = 'hr.employee'

    payroll_code = fields.Char(
        string='Payroll Code',
        help='Official employee code for payroll system (e.g., 0000013)'
    )


class TimesheetReport(models.Model):
    _name = 'timesheet.report'
    _description = 'Timesheet Report'
    _auto = False  # Database view model - no physical table

    # Basic fields from SQL view
    employee_id = fields.Many2one('hr.employee', string='Employee', readonly=True)
    date = fields.Date(string='Date', readonly=True)
    date_time = fields.Datetime(string="Start Time", readonly=True)
    end_time = fields.Datetime(string='End Time', readonly=True)
    total_hours = fields.Float(string='Total Hours', readonly=True)
    project_id = fields.Many2one('project.project', string='Project', readonly=True)
    task_id = fields.Many2one('project.task', string='Task', readonly=True)
    
    # Working hours fields
    office_hours = fields.Float(string='Office Hours (8:30-18:30)', readonly=True)
    hours_18_22 = fields.Float(string="Overtime 18-22", readonly=True)
    hours_22_06 = fields.Float(string="Night Overtime 22-06", readonly=True)
    
    # Day information fields
    day_of_week = fields.Char(string='Day Name', readonly=True)
    is_weekend = fields.Boolean(string='Is Weekend', readonly=True)
    
    # Delay calculation fields
    delay_hours = fields.Float(string='Delay Hours', readonly=True)
    delay_minutes = fields.Integer(string='Delay Minutes', readonly=True)
    is_delayed = fields.Boolean(string='Is Delayed', readonly=True)
    delay_display = fields.Char(string='Delay Time', readonly=True)
    
    # Leave fields
    leave_type = fields.Char(string='Leave Type', readonly=True)
    
    # Computed fields for UI display (not stored, only for presentation)
    colored_day_display = fields.Html(
        string='Day of Week',
        compute='_compute_day_info',
        sanitize=False
    )
    
    colored_delay_display = fields.Html(
        string="Delay (Colored)",
        compute="_compute_colored_delay_display",
        sanitize=False
    )
    
    hours_shortage = fields.Float(
        string='Hours Shortage',
        compute='_compute_hours_shortage',
        help='Hours shortage compared to 8 standard hours'
    )

    # Class-level cache for holidays
    _italy_holidays_cache = {}

    def _format_hours(self, hours_float):
        """Convert float to h:mm text format"""
        if hours_float is None:
            return "00:00"
        try:
            hours = int(hours_float)
            minutes = int(round((hours_float - hours) * 60))
            return f"{hours:02d}:{minutes:02d}"
        except (TypeError, ValueError):
            return "00:00"

    @classmethod
    def get_italy_holidays(cls, year):
        """
        Get Italian public holidays with caching.
        Cache is stored at class level to reduce API calls.
        """
        if not hasattr(cls, "_italy_holidays_cache"):
            cls._italy_holidays_cache = {}

        if year not in cls._italy_holidays_cache:
            holidays = set()
            try:
                url = f"https://date.nager.at/api/v3/PublicHolidays/{year}/IT"
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    for item in data:
                        holidays.add(item["date"])
                _logger.info(f"Fetched {len(holidays)} Italian holidays for year {year}")
            except requests.RequestException as e:
                _logger.warning(f"Failed to fetch Italian holidays for {year}: {e}")
            except Exception as e:
                _logger.error(f"Error processing holidays for {year}: {e}")
            
            cls._italy_holidays_cache[year] = holidays

        return cls._italy_holidays_cache[year]

    def _is_italian_holiday(self, date):
        """Check if date is an Italian public holiday"""
        if not date:
            return False
        year = date.year
        holidays = self.get_italy_holidays(year)
        date_str = date.strftime("%Y-%m-%d")
        return date_str in holidays

    @api.depends('date', 'day_of_week', 'is_weekend')
    def _compute_day_info(self):
        """Generate colored HTML badge for day display"""
        for rec in self:
            if not rec.date or not rec.day_of_week:
                rec.colored_day_display = ""
                continue

            day_name = rec.day_of_week
            is_holiday = rec.is_weekend or self._is_italian_holiday(rec.date)

            if is_holiday:
                rec.colored_day_display = f"""
                    <span style="
                        background-color: #ffdddd;
                        color: #a00;
                        padding: 3px 8px;
                        border-radius: 8px;
                        font-weight: bold;
                        font-size: 13px;
                        display: inline-block;
                        text-align: center;
                        min-width: 80px;">
                        {day_name}
                    </span>
                """
            else:
                rec.colored_day_display = f"""
                    <span style="
                        background-color: #ddffdd;
                        color: #060;
                        padding: 3px 8px;
                        border-radius: 8px;
                        font-weight: bold;
                        font-size: 13px;
                        display: inline-block;
                        text-align: center;
                        min-width: 80px;">
                        {day_name}
                    </span>
                """

    @api.depends('delay_display', 'is_delayed')
    def _compute_colored_delay_display(self):
        """Generate colored HTML badge for delay display"""
        for record in self:
            delay_text = record.delay_display or '0h 0m'
            if record.is_delayed:
                color = "#ffdddd"
                text_color = "#a00"
            else:
                color = "#ddffdd"
                text_color = "#060"
            record.colored_delay_display = f"""
                <span style="
                    background-color: {color};
                    color: {text_color};
                    padding: 3px 8px;
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 13px;
                    display: inline-block;
                    text-align: center;
                    min-width: 80px;">
                    {delay_text}
                </span>
            """

    @api.depends('total_hours')
    def _compute_hours_shortage(self):
        """Calculate shortage if worked less than 8 hours"""
        for record in self:
            if record.total_hours and record.total_hours < 8:
                record.hours_shortage = 8 - record.total_hours
            else:
                record.hours_shortage = 0.0

    def _get_leave_code(self, leave_type):
        """Map leave type name to official payroll code"""
        leave_codes = {
            'FE Ferie': 'FE',
            'V6 Assegno ordinar. pagam.diretto': 'V6',
            'Permesso (Ore)': 'Ore',
            'AI Assenza ingiustificata': 'AI',
            'A4 Quarantena sorv.attiva COVID19': 'A4',
            'AL Allattamento': 'AL',
            'C2 Solidarieta\'aut.DLsg 148/15': 'C2',
            'FR Cong.parentale a GG da 10 mesi ind.30%': 'FR',
            'C5 CIG aut.(maltempo)Evento CIG': 'C5',
            'C6 Solidarieta\' anticipata': 'C6',
            'F2 Flessibilita\' Tipo 2': 'F2',
            'FS Festività lavorata': 'FS',
            'IN Infortunio': 'IN',
            'LF Lavoro festivo': 'LF',
            'LN Supplementare notturno': 'LN',
            'LS Supplementare diurno': 'LS',
            'M1 Perm.retr. per MA bimbo < 3a': 'M1',
            'M2 Cong.parentale a HH da 7 a 9 mesi': 'M2',
            'M3 Mal. bambino < 3 anni (MA3)': 'M3',
            'M4  Prolung. congedo parentale disabili': 'M4',
            'M5 Cong.parentale a HH entro 6 mesi': 'M5',
            'M6 Cong.parentale a HH da 10 mesi non ind': 'M6',
            'M7 Cong.parentale a GG da 7 a 9 mesi': 'M7',
            'S5 Straord. porte chiuse festivo': 'S5',
            'S3 Straord. porte chiuse feriale': 'S3',
            'T3 Cig fondo solidarieta': 'T3',
            'S4 Straord. porte aperte festivo': 'S4',
            'SD Sospensione disciplinare': 'SD',
            'V1 Volontariato Protezione Civile': 'V1',
            'SC Sciopero': 'SC',
            'SN Straordinario notturno': 'SN',
            'ST Straordinario diurno': 'ST',
            'V2 Assenza ingiust. no green-pass': 'V2',
            'VV Cong. vittime violenza (DVV)': 'VV',
            'V9 Congedo quarant.figli DL111/20': 'V9',
            'VI Permessi Visite Inail': 'VI',
            'VM Permessi per visita medica': 'VM',
            'VO Cong. vittime viol.a ore (DVO)': 'VO',
            'A5 Assenza aut. sanitarie COVID19': 'A5',
            'A6 CIGO pagamento diretto': 'A6',
            'A8 Congedo genitor.retrib.COVID19': 'A8',
            'A9 Congedo genit.non retr.COVID19': 'A9',
            'AH Assenza assunti/dimessi': 'AH',
            'AP Aspettativa non retribuita': 'AP',
            'AR Aspettativa Retribuita': 'AR',
            'AS Assemblea sindacale': 'AS',
            'BO Permessi banca ore goduti': 'BO',
            'C1 Solidarieta\'antic.DLgs.148/15': 'C1',
            'C3 Cig autorizz.post D.Lgs.148/15': 'C3',
            'C4 CIG ant.(maltempo)Evento CIG': 'C4',
            'C9 CIG autorizz. Evento Maltempo': 'C9',
            'CA CIG anticipata': 'CA',
            'CC CIG autorizzata (no ctr.add.)': 'CC',
            'F1 Flessibilita\' Tipo 1': 'F1',
            'F3 Flessibilita\' Tipo 3': 'F3',
            'C7 Solidarieta\' autorizzata': 'C7',
            'F7 Ferie solidarieta\' autorizzata': 'F7',
            'C8 CIG anticipata Evento Maltempo': 'C8',
            'CB CIG autorizzata (si ctr.add.)': 'CB',
            'CP Congedo obbligatorio del padre': 'CP',
            'EM Emodialisi': 'EM',
            'CD Congedi straordinari disabili': 'CD',
            'CF Congedo facoltativo del padre': 'CF',
            'CI CIG non retribuita': 'CI',
            'CM Congedo matrimoniale': 'CM',
            'CV Perm. non retrib. Ctr virtuale': 'CV',
            'CY Morbo Cooley': 'CY',
            'DM Donazione midollo osseo': 'DM',
            'DS Donazione sangue': 'DS',
            'FG Flessibilita\' godute': 'FG',
            'GO Giornata ad orario ridotto-GOR': 'GO',
            'D2 Permessi disabili gg COVID19': 'D2',
            'MF Cong.parentale a GG entro 6 mesi': 'MF',
            'MI Militare': 'MI',
            'MM Malattia non conta per malus': 'MM',
            'MN Cong.parentale a GG da 10 mesi non ind': 'MN',
            'MO Malattia ospedaliera': 'MO',
            'MR Mancata certific.ricaduta mal.': 'MR',
            'MT Maternita\' obbligatoria': 'MT',
            'MX Malattia no trattam. speciale': 'MX',
        }
        return leave_codes.get(leave_type, 'OR')  # Default to 'OR' (ordinary)

    def generate_xml_report(self, domain=None):
        """
        Generate XML report for Italian payroll system.
        Uses Office Hours and Overtime calculations.
        """
        if domain is None:
            domain = []

        records = self.search(domain)

        # Create XML structure
        root = ET.Element("Fornitura")

        # Group records by employee_id
        employees = {}
        for record in records:
            employee_key = (record.employee_id.id, record.employee_id.name)
            if employee_key not in employees:
                employees[employee_key] = []
            employees[employee_key].append(record)

        # Process each employee
        for (emp_id, emp_name), emp_records in employees.items():
            employee_elem = ET.SubElement(root, "Dipendente")

            # Company code - should be configurable
            employee_elem.set("CodAziendaUfficiale", "000479")

            # Get employee payroll code from hr.employee
            employee = self.env['hr.employee'].browse(emp_id)
            employee_code = employee.payroll_code or str(emp_id).zfill(7)
            employee_elem.set("CodDipendenteUfficiale", employee_code)

            movimenti_elem = ET.SubElement(employee_elem, "Movimenti")
            movimenti_elem.set("GenerazioneAutomaticaDaTeorico", "N")

            # Process each record
            for record in emp_records:
                # Main movement for regular work hours
                if record.office_hours > 0 or record.leave_type:
                    movimento_elem = ET.SubElement(movimenti_elem, "Movimento")

                    # Determine code type
                    if record.leave_type:
                        cod_giustificativo = self._get_leave_code(record.leave_type)
                    else:
                        cod_giustificativo = "OR"  # Ordinary work

                    ET.SubElement(movimento_elem, "CodGiustificativoUfficiale").text = cod_giustificativo
                    ET.SubElement(movimento_elem, "Data").text = record.date.strftime("%Y-%m-%d") if record.date else ""

                    # Calculate hours and minutes
                    if record.office_hours > 0:
                        hours = int(record.office_hours)
                        minutes = int((record.office_hours - hours) * 60)
                    elif record.leave_type:
                        hours = 8  # Default 8 hours for leave
                        minutes = 0
                    else:
                        hours = 0
                        minutes = 0

                    ET.SubElement(movimento_elem, "NumOre").text = str(hours).zfill(2)
                    ET.SubElement(movimento_elem, "NumMinuti").text = str(minutes).zfill(2)

                # Overtime movement (18-22)
                if record.hours_18_22 and record.hours_18_22 > 0:
                    movimento_straordinario_elem = ET.SubElement(movimenti_elem, "Movimento")
                    ET.SubElement(movimento_straordinario_elem, "CodGiustificativoUfficiale").text = "ST"
                    ET.SubElement(movimento_straordinario_elem, "Data").text = record.date.strftime("%Y-%m-%d") if record.date else ""

                    hours_st = int(record.hours_18_22)
                    minutes_st = int((record.hours_18_22 - hours_st) * 60)
                    ET.SubElement(movimento_straordinario_elem, "NumOre").text = str(hours_st).zfill(2)
                    ET.SubElement(movimento_straordinario_elem, "NumMinuti").text = str(minutes_st).zfill(2)

                # Night overtime movement (22-06)
                if record.hours_22_06 and record.hours_22_06 > 0:
                    movimento_notturno_elem = ET.SubElement(movimenti_elem, "Movimento")
                    ET.SubElement(movimento_notturno_elem, "CodGiustificativoUfficiale").text = "STN"
                    ET.SubElement(movimento_notturno_elem, "Data").text = record.date.strftime("%Y-%m-%d") if record.date else ""

                    hours_notturno = int(record.hours_22_06)
                    minutes_notturno = int((record.hours_22_06 - hours_notturno) * 60)
                    ET.SubElement(movimento_notturno_elem, "NumOre").text = str(hours_notturno).zfill(2)
                    ET.SubElement(movimento_notturno_elem, "NumMinuti").text = str(minutes_notturno).zfill(2)

        # Convert to XML string with proper declaration
        xml_str = ET.tostring(root, encoding='utf-8', method='xml')
        return xml_str.decode('utf-8')

    def action_export_xml(self):
        """Action to download XML file"""
        domain = []
        if self._context.get('active_ids'):
            domain = [('id', 'in', self._context.get('active_ids'))]

        xml_content = self.generate_xml_report(domain)

        # Create attachment for download
        attachment = self.env['ir.attachment'].create({
            'name': 'timesheet_report_%s.xml' % fields.Date.today(),
            'datas': base64.b64encode(xml_content.encode('utf-8')),
            'type': 'binary',
            'mimetype': 'application/xml',
        })

        download_url = f'/web/content/{attachment.id}?download=true'

        return {
            "type": "ir.actions.act_url",
            "url": download_url,
            "target": "self",
        }

    def init(self):
        """
        Create the database view for timesheet report.
        This view combines timesheet entries with leave records.
        
        Time calculations are based on UTC (server timezone):
        - Office hours: 05:30-14:30 UTC (which is 08:30-17:30 in Europe/Rome winter)
        - Overtime 18-22: 15:00-19:00 UTC
        - Night overtime 22-06: 19:00-03:00 UTC
        """
        self.env.cr.execute("DROP VIEW IF EXISTS timesheet_report")

        self.env.cr.execute("""
            CREATE OR REPLACE VIEW timesheet_report AS (
                -- Timesheet section
                SELECT
                    min(ts.id) AS id,
                    ts.employee_id,
                    ts.date,
                    ts.project_id,
                    ts.task_id,
                    min(ts.date_time) AS date_time,
                    min(ts.date_time) + ((sum(ts.unit_amount) || ' hours')::interval) AS end_time,
                    COALESCE(sum(ts.unit_amount), 0) AS total_hours,

                    -- Calculate office_hours (max 8 hours)
                    -- Office range: 05:30-14:30 UTC
                    LEAST(COALESCE(
                        CASE 
                            WHEN min(ts.date_time) IS NOT NULL AND COALESCE(sum(ts.unit_amount), 0) > 0 THEN
                                EXTRACT(EPOCH FROM GREATEST(
                                    LEAST(
                                        min(ts.date_time) + ((COALESCE(sum(ts.unit_amount), 0) || ' hours')::interval),
                                        date_trunc('day', min(ts.date_time)) + interval '14 hours 30 minutes'
                                    ) - GREATEST(
                                        min(ts.date_time),
                                        date_trunc('day', min(ts.date_time)) + interval '5 hours 30 minutes'
                                    ),
                                    interval '0 second'
                                )) / 3600
                            ELSE 0
                        END, 0
                    ), 8.0) AS office_hours,

                    -- Calculate hours_18_22 (overtime in 18-22 range plus hours above 8)
                    COALESCE(
                        EXTRACT(EPOCH FROM GREATEST(
                            LEAST(
                                min(ts.date_time) + ((sum(ts.unit_amount) || ' hours')::interval),
                                date_trunc('day', min(ts.date_time)) + interval '22 hours'
                            ) - GREATEST(
                                min(ts.date_time),
                                date_trunc('day', min(ts.date_time)) + interval '18 hours'
                            ),
                            interval '0 second'
                        )) / 3600, 0
                    ) + GREATEST(0, COALESCE(sum(ts.unit_amount), 0) - 8.0) AS hours_18_22,

                    -- Calculate hours_22_06 (night overtime)
                    COALESCE(
                        EXTRACT(EPOCH FROM GREATEST(
                            LEAST(
                                min(ts.date_time) + ((sum(ts.unit_amount) || ' hours')::interval),
                                date_trunc('day', min(ts.date_time)) + interval '1 day' + interval '3 hours 30 minutes'
                            ) - GREATEST(
                                min(ts.date_time),
                                date_trunc('day', min(ts.date_time)) + interval '18 hours 30 minutes'
                            ),
                            interval '0 second'
                        )) / 3600, 0
                    ) AS hours_22_06,

                    -- Day of week
                    CASE 
                        WHEN EXTRACT(DOW FROM ts.date) = 0 THEN 'Sunday'
                        WHEN EXTRACT(DOW FROM ts.date) = 1 THEN 'Monday'
                        WHEN EXTRACT(DOW FROM ts.date) = 2 THEN 'Tuesday'
                        WHEN EXTRACT(DOW FROM ts.date) = 3 THEN 'Wednesday'
                        WHEN EXTRACT(DOW FROM ts.date) = 4 THEN 'Thursday'
                        WHEN EXTRACT(DOW FROM ts.date) = 5 THEN 'Friday'
                        WHEN EXTRACT(DOW FROM ts.date) = 6 THEN 'Saturday'
                    END AS day_of_week,

                    -- Is weekend
                    CASE 
                        WHEN EXTRACT(DOW FROM ts.date) IN (0, 6) THEN true
                        ELSE false
                    END AS is_weekend,

                    -- Delay calculations (comparing to 05:30 UTC = 08:30 local)
                    CASE 
                        WHEN MIN(ts.date_time) > (date_trunc('day', MIN(ts.date_time)) + interval '5 hours 30 minutes')
                        THEN EXTRACT(EPOCH FROM (MIN(ts.date_time) - (date_trunc('day', MIN(ts.date_time)) + interval '5 hours 30 minutes'))) / 3600
                        ELSE 0
                    END AS delay_hours,

                    CASE 
                        WHEN MIN(ts.date_time) > (date_trunc('day', MIN(ts.date_time)) + interval '5 hours 30 minutes') 
                        THEN EXTRACT(EPOCH FROM (MIN(ts.date_time) - (date_trunc('day', MIN(ts.date_time)) + interval '5 hours 30 minutes'))) / 60
                        ELSE 0
                    END::integer AS delay_minutes,

                    CASE 
                        WHEN MIN(ts.date_time) > (date_trunc('day', MIN(ts.date_time)) + interval '5 hours 30 minutes')
                        THEN true
                        ELSE false
                    END AS is_delayed,

                    CASE
                        WHEN MIN(ts.date_time) > (date_trunc('day', MIN(ts.date_time)) + interval '5 hours 30 minutes')
                        THEN 
                            (FLOOR(EXTRACT(EPOCH FROM (MIN(ts.date_time) - (date_trunc('day', MIN(ts.date_time)) + interval '5 hours 30 minutes'))) / 3600)::text
                            || 'h ' ||
                            FLOOR(
                                MOD(
                                    EXTRACT(EPOCH FROM (MIN(ts.date_time) - (date_trunc('day', MIN(ts.date_time)) + interval '5 hours 30 minutes')))::numeric,
                                    3600
                                ) / 60
                            )::text
                            || 'm')
                        ELSE '0h 0m'
                    END AS delay_display,

                    -- Leave type (NULL for timesheet entries)
                    NULL::varchar AS leave_type

                FROM account_analytic_line ts
                WHERE ts.project_id IS NOT NULL 
                  AND ts.employee_id IS NOT NULL
                  AND ts.unit_amount > 0
                GROUP BY ts.employee_id, ts.date, ts.project_id, ts.task_id

                UNION ALL

                -- Leave section
                SELECT
                    -hl.id AS id,
                    hl.employee_id,
                    hl.request_date_from::date AS date,
                    NULL::integer AS project_id,
                    NULL::integer AS task_id,
                    hl.request_date_from::timestamp AS date_time,
                    hl.request_date_to::timestamp AS end_time,
                    0::float AS total_hours,
                    0::float AS office_hours,
                    0::float AS hours_18_22,
                    0::float AS hours_22_06,
                    CASE 
                        WHEN EXTRACT(DOW FROM hl.request_date_from) = 0 THEN 'Sunday'
                        WHEN EXTRACT(DOW FROM hl.request_date_from) = 1 THEN 'Monday'
                        WHEN EXTRACT(DOW FROM hl.request_date_from) = 2 THEN 'Tuesday'
                        WHEN EXTRACT(DOW FROM hl.request_date_from) = 3 THEN 'Wednesday'
                        WHEN EXTRACT(DOW FROM hl.request_date_from) = 4 THEN 'Thursday'
                        WHEN EXTRACT(DOW FROM hl.request_date_from) = 5 THEN 'Friday'
                        WHEN EXTRACT(DOW FROM hl.request_date_from) = 6 THEN 'Saturday'
                    END AS day_of_week,
                    CASE 
                        WHEN EXTRACT(DOW FROM hl.request_date_from) IN (0, 6) THEN true
                        ELSE false
                    END AS is_weekend,
                    0::float AS delay_hours,
                    0::integer AS delay_minutes,
                    false AS is_delayed,
                    '0h 0m'::varchar AS delay_display,
                    -- Extract leave type name from translatable jsonb field
                    COALESCE(
                        ltype.name->>'en_US', 
                        ltype.name->>'fa_IR', 
                        ltype.name->>'it_IT',
                        (SELECT value FROM jsonb_each_text(ltype.name) LIMIT 1)
                    )::varchar AS leave_type
                FROM hr_leave hl
                JOIN hr_leave_type ltype ON ltype.id = hl.holiday_status_id
                WHERE hl.state = 'validate'
            )
        """)
