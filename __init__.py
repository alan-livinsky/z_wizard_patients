from trytond.pool import Pool

from . import wizard


def register():
    Pool.register(
        wizard.DomiciliaryUnit,
        wizard.QuickPatientLookup,
        wizard.QuickPatientDetails,
        module='z_wizard_patients', type_='model')
    Pool.register(
        wizard.QuickPatientWizard,
        module='z_wizard_patients', type_='wizard')
