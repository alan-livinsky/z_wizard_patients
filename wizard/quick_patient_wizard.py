from trytond.exceptions import UserError
from trytond.i18n import gettext
from trytond.model import ModelView, fields
from trytond.pool import Pool
from trytond.pyson import Eval
from trytond.wizard import Button, StateAction, StateTransition, StateView, Wizard


def _clean(value):
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


class QuickPatientPersonal(ModelView):
    'Quick Patient Personal'
    __name__ = 'z_wizard_patients.quick_patient.personal'

    first_name = fields.Char('Nombre', required=True)
    last_name = fields.Char('Apellido', required=True)
    ref = fields.Char('DNI / mocIDUP', required=True)
    gender = fields.Selection([
        (None, ''),
        ('m', 'Male'),
        ('f', 'Female'),
        ('nb', 'Non-binary'),
        ('other', 'Other'),
        ('nd', 'Non disclosed'),
        ('u', 'Unknown'),
    ], 'Genero', required=True, sort=False)


class QuickPatientAddress(ModelView):
    'Quick Patient Address'
    __name__ = 'z_wizard_patients.quick_patient.address'

    street = fields.Char('Calle', required=True)
    street_number = fields.Char('Numero')
    unit = fields.Char('Unidad')
    municipality = fields.Char('Municipio')
    city = fields.Char('Ciudad', required=True)
    zip = fields.Char('Codigo Postal')
    country = fields.Many2One('country.country', 'Pais', required=True)
    subdivision = fields.Many2One(
        'country.subdivision', 'Provincia',
        domain=[('country', '=', Eval('country'))],
        depends=['country'])


class QuickPatientInsurance(ModelView):
    'Quick Patient Insurance'
    __name__ = 'z_wizard_patients.quick_patient.insurance'

    insurance_company = fields.Many2One(
        'party.party', 'Obra Social', required=True,
        domain=[('is_insurance_company', '=', True)])
    insurance_number = fields.Char('Numero de Afiliado', required=True)
    insurance_plan = fields.Many2One(
        'gnuhealth.insurance.plan', 'Plan',
        domain=[('company', '=', Eval('insurance_company'))],
        depends=['insurance_company'])


class QuickPatientConfirm(ModelView):
    'Quick Patient Confirm'
    __name__ = 'z_wizard_patients.quick_patient.confirm'

    summary = fields.Text('Resumen', readonly=True)


class QuickPatientWizard(Wizard):
    'Quick Patient Wizard'
    __name__ = 'wizard.gnuhealth.patient.quick_create'

    start_state = 'personal'

    personal = StateView(
        'z_wizard_patients.quick_patient.personal',
        'z_wizard_patients.quick_patient_personal_view_form', [
            Button('Cancelar', 'end', 'tryton-cancel'),
            Button('Siguiente', 'personal_next', 'tryton-forward', default=True),
        ])
    personal_next = StateTransition()

    address = StateView(
        'z_wizard_patients.quick_patient.address',
        'z_wizard_patients.quick_patient_address_view_form', [
            Button('Anterior', 'address_previous', 'tryton-back'),
            Button('Siguiente', 'address_next', 'tryton-forward', default=True),
        ])
    address_previous = StateTransition()
    address_next = StateTransition()

    insurance = StateView(
        'z_wizard_patients.quick_patient.insurance',
        'z_wizard_patients.quick_patient_insurance_view_form', [
            Button('Anterior', 'insurance_previous', 'tryton-back'),
            Button('Siguiente', 'insurance_next', 'tryton-forward', default=True),
        ])
    insurance_previous = StateTransition()
    insurance_next = StateTransition()

    confirm = StateView(
        'z_wizard_patients.quick_patient.confirm',
        'z_wizard_patients.quick_patient_confirm_view_form', [
            Button('Anterior', 'confirm_previous', 'tryton-back'),
            Button('Crear', 'create_patient', 'tryton-ok', default=True),
        ])
    confirm_previous = StateTransition()

    create_patient = StateAction('health.action_gnuhealth_patient_view')

    @staticmethod
    def _state_values(state, names):
        values = {}
        if not state:
            return values
        state_values = getattr(state, '_values', None) or {}
        for name in names:
            if name in state_values:
                values[name] = state_values[name]
        return values

    def transition_personal_next(self):
        self._ensure_personal_data()
        return 'address'

    def transition_address_previous(self):
        return 'personal'

    def transition_address_next(self):
        self._ensure_address_data()
        return 'insurance'

    def transition_insurance_previous(self):
        return 'address'

    def transition_insurance_next(self):
        self._ensure_insurance_data()
        self._check_existing_patient()
        return 'confirm'

    def transition_confirm_previous(self):
        return 'insurance'

    def default_personal(self, fields_):
        return self._state_values(getattr(self, 'personal', None), [
            'first_name', 'last_name', 'ref', 'gender',
        ])

    def default_address(self, fields_):
        defaults = self._state_values(getattr(self, 'address', None), [
            'street', 'street_number', 'unit', 'municipality', 'city', 'zip',
            'country', 'subdivision',
        ])
        if not defaults:
            DomiciliaryUnit = Pool().get('gnuhealth.du')
            defaults['country'] = DomiciliaryUnit.default_address_country()
        return defaults

    def default_insurance(self, fields_):
        return self._state_values(getattr(self, 'insurance', None), [
            'insurance_company', 'insurance_number', 'insurance_plan',
        ])

    def default_confirm(self, fields_):
        return {
            'summary': self._build_summary(),
        }

    def do_create_patient(self, action):
        patient_id = self._create_or_update_records()
        action['views'].reverse()
        return action, {'res_id': [patient_id]}

    def transition_create_patient(self):
        return 'end'

    def _ensure_personal_data(self):
        if not _clean(self.personal.first_name):
            raise UserError(gettext(
                'z_wizard_patients.msg_missing_first_name'))
        if not _clean(self.personal.last_name):
            raise UserError(gettext(
                'z_wizard_patients.msg_missing_last_name'))
        if not _clean(self.personal.ref):
            raise UserError(gettext(
                'z_wizard_patients.msg_missing_ref'))
        if not self.personal.gender:
            raise UserError(gettext(
                'z_wizard_patients.msg_missing_gender'))

    def _ensure_address_data(self):
        if not _clean(self.address.street):
            raise UserError(gettext(
                'z_wizard_patients.msg_missing_street'))
        if not _clean(self.address.city):
            raise UserError(gettext(
                'z_wizard_patients.msg_missing_city'))
        if not self.address.country:
            raise UserError(gettext(
                'z_wizard_patients.msg_missing_country'))

    def _ensure_insurance_data(self):
        if not self.insurance.insurance_company:
            raise UserError(gettext(
                'z_wizard_patients.msg_missing_insurance_company'))
        if not _clean(self.insurance.insurance_number):
            raise UserError(gettext(
                'z_wizard_patients.msg_missing_insurance_number'))

    def _get_party_by_ref(self):
        Party = Pool().get('party.party')
        ref = _clean(self.personal.ref)
        parties = Party.search([('ref', '=', ref)])
        if len(parties) > 1:
            raise UserError(gettext(
                'z_wizard_patients.msg_duplicate_party_for_ref',
                ref=ref))
        return parties[0] if parties else None

    def _get_patient_for_party(self, party):
        Patient = Pool().get('gnuhealth.patient')
        patients = Patient.search([('name', '=', party.id)], limit=1)
        return patients[0] if patients else None

    def _check_existing_patient(self):
        party = self._get_party_by_ref()
        if not party:
            return
        patient = self._get_patient_for_party(party)
        if patient:
            raise UserError(gettext(
                'z_wizard_patients.msg_patient_already_exists',
                patient=patient.rec_name,
                ref=party.ref))

    def _build_summary(self):
        party = self._get_party_by_ref()
        lines = [
            gettext('z_wizard_patients.msg_summary_person',
                    first_name=_clean(self.personal.first_name),
                    last_name=_clean(self.personal.last_name),
                    ref=_clean(self.personal.ref)),
            gettext('z_wizard_patients.msg_summary_address',
                    street=_clean(self.address.street),
                    street_number=_clean(self.address.street_number) or '-',
                    unit=_clean(self.address.unit) or '-',
                    city=_clean(self.address.city),
                    zip=_clean(self.address.zip) or '-'),
            gettext('z_wizard_patients.msg_summary_insurance',
                    company=self.insurance.insurance_company.rec_name,
                    number=_clean(self.insurance.insurance_number),
                    plan=(
                        self.insurance.insurance_plan.rec_name
                        if self.insurance.insurance_plan else '-')),
        ]
        if party:
            lines.append('')
            lines.append(gettext(
                'z_wizard_patients.msg_existing_party_notice',
                party=party.rec_name,
                ref=party.ref))
            lines.append(gettext(
                'z_wizard_patients.msg_existing_party_fill_only_empty'))
        return '\n'.join(lines)

    def _create_or_update_records(self):
        pool = Pool()
        Party = pool.get('party.party')
        Patient = pool.get('gnuhealth.patient')
        DomiciliaryUnit = pool.get('gnuhealth.du')
        Address = pool.get('party.address')
        Insurance = pool.get('gnuhealth.insurance')

        party = self._get_party_by_ref()
        if party:
            self._update_existing_party(party, Party)
        else:
            party, = Party.create([self._get_party_values()])

        if party.du:
            self._fill_du_if_empty(party.du, DomiciliaryUnit)
        else:
            du, = DomiciliaryUnit.create([self._get_du_values()])
            Party.write([party], {'du': du.id})

        billing_address = party.addresses[0] if party.addresses else None
        if billing_address:
            self._fill_billing_address_if_empty(billing_address, Address)
        else:
            Address.create([self._get_address_values(party.id)])

        insurance = self._get_or_create_insurance(party, Insurance)

        patient = self._get_patient_for_party(party)
        if patient:
            Patient.write([patient], {'current_insurance': insurance.id})
        else:
            patient, = Patient.create([{
                'name': party.id,
                'current_insurance': insurance.id,
            }])
        return patient.id

    def _get_party_values(self):
        return {
            'name': _clean(self.personal.first_name),
            'lastname': _clean(self.personal.last_name),
            'ref': _clean(self.personal.ref),
            'gender': self.personal.gender,
            'is_person': True,
            'is_patient': True,
        }

    def _update_existing_party(self, party, Party):
        values = {}
        if not party.name and _clean(self.personal.first_name):
            values['name'] = _clean(self.personal.first_name)
        if not party.lastname and _clean(self.personal.last_name):
            values['lastname'] = _clean(self.personal.last_name)
        if not party.gender and self.personal.gender:
            values['gender'] = self.personal.gender
        if not party.ref and _clean(self.personal.ref):
            values['ref'] = _clean(self.personal.ref)
        if not party.is_person:
            values['is_person'] = True
        if not party.is_patient:
            values['is_patient'] = True
        if values:
            Party.write([party], values)

    def _generate_du_code(self):
        DomiciliaryUnit = Pool().get('gnuhealth.du')
        base = 'DU-%s' % _clean(self.personal.ref)
        code = base
        index = 1
        while DomiciliaryUnit.search([('name', '=', code)], limit=1):
            index += 1
            code = '%s-%s' % (base, index)
        return code

    def _get_du_values(self):
        return {
            'name': self._generate_du_code(),
            'desc': '%s %s' % (
                _clean(self.personal.first_name),
                _clean(self.personal.last_name)),
            'address_street': _clean(self.address.street),
            'address_street_number': _clean(self.address.street_number),
            'address_street_bis': _clean(self.address.unit),
            'address_municipality': _clean(self.address.municipality),
            'address_city': _clean(self.address.city),
            'address_zip': _clean(self.address.zip),
            'address_country': self.address.country.id,
            'address_subdivision': (
                self.address.subdivision.id if self.address.subdivision else None
            ),
        }

    def _fill_du_if_empty(self, du, DomiciliaryUnit):
        values = {}
        for field_name, value in [
                ('desc', '%s %s' % (
                    _clean(self.personal.first_name), _clean(self.personal.last_name))),
                ('address_street', _clean(self.address.street)),
                ('address_street_number', _clean(self.address.street_number)),
                ('address_street_bis', _clean(self.address.unit)),
                ('address_municipality', _clean(self.address.municipality)),
                ('address_city', _clean(self.address.city)),
                ('address_zip', _clean(self.address.zip))]:
            if not getattr(du, field_name) and value:
                values[field_name] = value
        if not du.address_country and self.address.country:
            values['address_country'] = self.address.country.id
        if not du.address_subdivision and self.address.subdivision:
            values['address_subdivision'] = self.address.subdivision.id
        if values:
            DomiciliaryUnit.write([du], values)

    def _get_address_values(self, party_id):
        return {
            'party': party_id,
            'street': self._compose_street(),
            'city': _clean(self.address.city),
            'zip': _clean(self.address.zip),
            'country': self.address.country.id,
            'subdivision': (
                self.address.subdivision.id if self.address.subdivision else None
            ),
        }

    def _fill_billing_address_if_empty(self, address, Address):
        values = {}
        street = self._compose_street()
        if not address.street and street:
            values['street'] = street
        if not address.city and _clean(self.address.city):
            values['city'] = _clean(self.address.city)
        if not address.zip and _clean(self.address.zip):
            values['zip'] = _clean(self.address.zip)
        if not address.country and self.address.country:
            values['country'] = self.address.country.id
        if not address.subdivision and self.address.subdivision:
            values['subdivision'] = self.address.subdivision.id
        if values:
            Address.write([address], values)

    def _compose_street(self):
        parts = [
            _clean(self.address.street),
            _clean(self.address.street_number),
            _clean(self.address.unit),
        ]
        return ' '.join([part for part in parts if part])

    def _get_or_create_insurance(self, party, Insurance):
        company = self.insurance.insurance_company
        number = _clean(self.insurance.insurance_number)
        plan = self.insurance.insurance_plan

        insurance = Insurance.search([
            ('company', '=', company.id),
            ('number', '=', number),
        ], limit=1)
        if insurance:
            insurance = insurance[0]
            if insurance.name and insurance.name.id != party.id:
                raise UserError(gettext(
                    'z_wizard_patients.msg_insurance_number_in_use',
                    company=company.rec_name,
                    number=number))
            values = {}
            if not insurance.name:
                values['name'] = party.id
            if not insurance.plan_id and plan:
                values['plan_id'] = plan.id
            if values:
                Insurance.write([insurance], values)
            return insurance

        values = {
            'name': party.id,
            'company': company.id,
            'number': number,
        }
        if plan:
            values['plan_id'] = plan.id
        insurance, = Insurance.create([values])
        return insurance
