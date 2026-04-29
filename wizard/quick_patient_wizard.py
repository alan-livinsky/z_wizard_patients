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


class QuickPatientLookup(ModelView):
    'Quick Patient Lookup'
    __name__ = 'z_wizard_patients.quick_patient.lookup'

    ref = fields.Char('DNI / mocIDUP', required=True)


class QuickPatientDetails(ModelView):
    'Quick Patient Details'
    __name__ = 'z_wizard_patients.quick_patient.details'

    ref = fields.Char('DNI / mocIDUP', readonly=True)
    existing_party_notice = fields.Text('Aviso', readonly=True)
    first_name = fields.Char('Nombre', required=True)
    last_name = fields.Char('Apellido', required=True)
    gender = fields.Selection([
        (None, ''),
        ('m', 'Masculino'),
        ('f', 'Femenino'),
        ('nb', 'No binario'),
        ('other', 'Otro'),
        ('nd', 'Prefiere no informar'),
        ('u', 'Desconocido'),
    ], 'Genero', required=True, sort=False)
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
    insurance_company = fields.Many2One(
        'party.party', 'Obra Social', required=True,
        domain=[('is_insurance_company', '=', True)])
    insurance_number = fields.Char('Numero de Afiliado', required=True)
    insurance_plan = fields.Many2One(
        'gnuhealth.insurance.plan', 'Plan',
        domain=[('company', '=', Eval('insurance_company'))],
        depends=['insurance_company'])


class QuickPatientWizard(Wizard):
    'Quick Patient Wizard'
    __name__ = 'wizard.gnuhealth.patient.quick_create'

    start_state = 'lookup'

    lookup = StateView(
        'z_wizard_patients.quick_patient.lookup',
        'z_wizard_patients.quick_patient_lookup_view_form', [
            Button('Cancelar', 'end', 'tryton-cancel'),
            Button('Siguiente', 'lookup_next', 'tryton-forward', default=True),
        ])
    lookup_next = StateTransition()

    details = StateView(
        'z_wizard_patients.quick_patient.details',
        'z_wizard_patients.quick_patient_details_view_form', [
            Button('Anterior', 'details_previous', 'tryton-back'),
            Button('Crear', 'create_patient', 'tryton-ok', default=True),
        ])
    details_previous = StateTransition()

    open_existing = StateAction('health.action_gnuhealth_patient_view')
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

    def transition_lookup_next(self):
        self._ensure_lookup_data()
        if self._get_existing_patient():
            return 'open_existing'
        return 'details'

    def transition_details_previous(self):
        return 'lookup'

    def default_lookup(self, fields_):
        return self._state_values(getattr(self, 'lookup', None), ['ref'])

    def default_details(self, fields_):
        defaults = self._state_values(getattr(self, 'details', None), [
            'ref', 'existing_party_notice', 'first_name', 'last_name',
            'gender', 'street', 'street_number', 'unit', 'municipality',
            'city', 'zip', 'country', 'subdivision', 'insurance_company',
            'insurance_number', 'insurance_plan',
        ])
        if defaults and defaults.get('ref') == self._get_ref():
            return defaults

        defaults = {
            'ref': self._get_ref(),
            'country': self._default_country(),
        }
        party = self._get_party_by_ref()
        if not party:
            return defaults

        defaults.update(self._without_empty(
            self._get_existing_party_defaults(party)))
        defaults['existing_party_notice'] = '\n'.join([
            gettext(
                'z_wizard_patients.msg_existing_party_notice',
                party=party.rec_name,
                ref=party.ref),
            gettext('z_wizard_patients.msg_existing_party_fill_only_empty'),
        ])
        return defaults

    def do_open_existing(self, action):
        patient = self._get_existing_patient()
        if not patient:
            return action, {}
        action['views'].reverse()
        action['name'] = gettext(
            'z_wizard_patients.msg_existing_patient_opening',
            patient=patient.rec_name,
            ref=self._get_ref())
        return action, {'res_id': [patient.id]}

    def transition_open_existing(self):
        return 'end'

    def do_create_patient(self, action):
        self._ensure_details_data()
        patient_id = self._create_or_update_records()
        action['views'].reverse()
        return action, {'res_id': [patient_id]}

    def transition_create_patient(self):
        return 'end'

    @staticmethod
    def _default_country():
        Country = Pool().get('country.country')
        countries = Country.search([
            ('code', '=', 'AR'),
        ], limit=1)
        if countries:
            return countries[0].id

        DomiciliaryUnit = Pool().get('gnuhealth.du')
        return DomiciliaryUnit.default_address_country()

    def _get_ref(self):
        lookup = getattr(self, 'lookup', None)
        return _clean(lookup.ref) if lookup else None

    def _ensure_lookup_data(self):
        if not self._get_ref():
            raise UserError(gettext(
                'z_wizard_patients.msg_missing_ref'))

    def _ensure_details_data(self):
        if not _clean(self.details.first_name):
            raise UserError(gettext(
                'z_wizard_patients.msg_missing_first_name'))
        if not _clean(self.details.last_name):
            raise UserError(gettext(
                'z_wizard_patients.msg_missing_last_name'))
        if not self.details.gender:
            raise UserError(gettext(
                'z_wizard_patients.msg_missing_gender'))
        if not _clean(self.details.street):
            raise UserError(gettext(
                'z_wizard_patients.msg_missing_street'))
        if not _clean(self.details.city):
            raise UserError(gettext(
                'z_wizard_patients.msg_missing_city'))
        if not self.details.country:
            raise UserError(gettext(
                'z_wizard_patients.msg_missing_country'))
        if not self.details.insurance_company:
            raise UserError(gettext(
                'z_wizard_patients.msg_missing_insurance_company'))
        if not _clean(self.details.insurance_number):
            raise UserError(gettext(
                'z_wizard_patients.msg_missing_insurance_number'))

    def _get_party_by_ref(self, ref=None):
        Party = Pool().get('party.party')
        ref = _clean(ref if ref is not None else self._get_ref())
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

    def _get_existing_patient(self):
        party = self._get_party_by_ref()
        if not party:
            return None
        return self._get_patient_for_party(party)

    def _get_existing_insurance(self, party):
        Insurance = Pool().get('gnuhealth.insurance')
        insurances = Insurance.search([
            ('name', '=', party.id),
        ], limit=1)
        return insurances[0] if insurances else None

    def _get_existing_party_defaults(self, party):
        defaults = {
            'first_name': party.name,
            'last_name': party.lastname,
            'gender': party.gender,
        }

        du = getattr(party, 'du', None)
        address = party.addresses[0] if party.addresses else None
        insurance = self._get_existing_insurance(party)

        if du:
            defaults.update({
                'street': du.address_street,
                'street_number': du.address_street_number,
                'unit': du.address_street_bis,
                'municipality': du.address_municipality,
                'city': du.address_city,
                'zip': du.address_zip,
                'country': du.address_country.id if du.address_country else None,
                'subdivision': (
                    du.address_subdivision.id
                    if du.address_subdivision else None),
            })
        elif address:
            defaults.update({
                'street': address.street,
                'city': address.city,
                'zip': address.zip,
                'country': address.country.id if address.country else None,
                'subdivision': (
                    address.subdivision.id if address.subdivision else None),
            })

        if insurance:
            defaults.update({
                'insurance_company': (
                    insurance.company.id if insurance.company else None),
                'insurance_number': insurance.number,
                'insurance_plan': (
                    insurance.plan_id.id if insurance.plan_id else None),
            })

        return defaults

    @staticmethod
    def _without_empty(values):
        return {
            key: value for key, value in values.items()
            if value not in (None, '')
        }

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
        Party = Pool().get('party.party')
        return {
            'name': _clean(self.details.first_name),
            'lastname': _clean(self.details.last_name),
            'ref': self._get_ref(),
            'gender': self.details.gender,
            'fed_country': Party.default_fed_country(),
            'citizenship': Party.default_citizenship(),
            'residence': Party.default_residence(),
            'is_person': True,
            'is_patient': True,
        }

    def _update_existing_party(self, party, Party):
        values = {}
        if not party.name and _clean(self.details.first_name):
            values['name'] = _clean(self.details.first_name)
        if not party.lastname and _clean(self.details.last_name):
            values['lastname'] = _clean(self.details.last_name)
        if not party.gender and self.details.gender:
            values['gender'] = self.details.gender
        if not party.ref and self._get_ref():
            values['ref'] = self._get_ref()
        if not party.is_person:
            values['is_person'] = True
        if not party.is_patient:
            values['is_patient'] = True
        if values:
            Party.write([party], values)

    def _generate_du_code(self):
        DomiciliaryUnit = Pool().get('gnuhealth.du')
        base = 'DU-%s' % self._get_ref()
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
                _clean(self.details.first_name),
                _clean(self.details.last_name)),
            'address_street': _clean(self.details.street),
            'address_street_number': _clean(self.details.street_number),
            'address_street_bis': _clean(self.details.unit),
            'address_municipality': _clean(self.details.municipality),
            'address_city': _clean(self.details.city),
            'address_zip': _clean(self.details.zip),
            'address_country': self.details.country.id,
            'address_subdivision': (
                self.details.subdivision.id if self.details.subdivision else None
            ),
        }

    def _fill_du_if_empty(self, du, DomiciliaryUnit):
        values = {}
        for field_name, value in [
                ('desc', '%s %s' % (
                    _clean(self.details.first_name),
                    _clean(self.details.last_name))),
                ('address_street', _clean(self.details.street)),
                ('address_street_number', _clean(self.details.street_number)),
                ('address_street_bis', _clean(self.details.unit)),
                ('address_municipality', _clean(self.details.municipality)),
                ('address_city', _clean(self.details.city)),
                ('address_zip', _clean(self.details.zip))]:
            if not getattr(du, field_name) and value:
                values[field_name] = value
        if not du.address_country and self.details.country:
            values['address_country'] = self.details.country.id
        if not du.address_subdivision and self.details.subdivision:
            values['address_subdivision'] = self.details.subdivision.id
        if values:
            DomiciliaryUnit.write([du], values)

    def _get_address_values(self, party_id):
        return {
            'party': party_id,
            'street': self._compose_street(),
            'city': _clean(self.details.city),
            'zip': _clean(self.details.zip),
            'country': self.details.country.id,
            'subdivision': (
                self.details.subdivision.id if self.details.subdivision else None
            ),
        }

    def _fill_billing_address_if_empty(self, address, Address):
        values = {}
        street = self._compose_street()
        if not address.street and street:
            values['street'] = street
        if not address.city and _clean(self.details.city):
            values['city'] = _clean(self.details.city)
        if not address.zip and _clean(self.details.zip):
            values['zip'] = _clean(self.details.zip)
        if not address.country and self.details.country:
            values['country'] = self.details.country.id
        if not address.subdivision and self.details.subdivision:
            values['subdivision'] = self.details.subdivision.id
        if values:
            Address.write([address], values)

    def _compose_street(self):
        parts = [
            _clean(self.details.street),
            _clean(self.details.street_number),
            _clean(self.details.unit),
        ]
        return ' '.join([part for part in parts if part])

    def _get_or_create_insurance(self, party, Insurance):
        company = self.details.insurance_company
        number = _clean(self.details.insurance_number)
        plan = self.details.insurance_plan

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
