Quick Patient Wizard
====================

This module adds a GNU Health / Tryton wizard for fast patient admission.

Workflow
--------

* First screen: asks only for ``DNI / mocIDUP``.
* If the DNI already belongs to an existing patient, the wizard opens that
  patient record instead of continuing the intake flow.
* If the DNI can be used for intake, the wizard shows a single follow-up
  screen with personal data, address and insurance fields.
* The wizard saves directly from that combined screen without a separate
  confirmation step.

Features
--------

* Creates or reuses the related ``party.party`` record.
* Creates the ``gnuhealth.patient`` record.
* Creates the main ``gnuhealth.du`` record.
* Copies the same address to ``party.address`` for billing and
  administrative use.
* Creates the patient's ``gnuhealth.insurance`` and assigns it as
  ``current_insurance``.

Business rules
--------------

* DNI / mocIDUP is stored in ``party.ref``.
* If the DNI already exists:

  * If the related patient already exists, the wizard opens that patient
    record.
  * If the party exists without patient, the wizard reuses that party and
    completes only missing data.

* Existing data is never overwritten automatically.

Installation
------------

1. Clone the repository on the target server.
2. Install the module locally:

   ``pip install /path/to/repo/z_wizard_patients``

3. Update the Tryton module list.
4. Install ``z_wizard_patients`` from the Tryton administration interface.

Compatibility
-------------

* Python 3.10
* Tryton 6.0
* GNU Health 4.2
