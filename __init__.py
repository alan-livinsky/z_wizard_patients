from trytond.pool import Pool

from . import wizard


def register():
    Pool.register(
        wizard.QuickPatientPersonal,
        wizard.QuickPatientAddress,
        wizard.QuickPatientInsurance,
        wizard.QuickPatientConfirm,
        module='z_wizard_patients', type_='model')
    Pool.register(
        wizard.QuickPatientWizard,
        module='z_wizard_patients', type_='wizard')
