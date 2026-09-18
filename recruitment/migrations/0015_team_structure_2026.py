from django.db import migrations

# Sub-team structure for the 2026/27 season, confirmed by the VP on
# 18 September 2026. This migration only sets the starting point: edit
# names, taglines and the recruiting toggle in the admin afterwards.
#
# Air is a joint programme with UGA (University of Glasgow Aero). Their
# sub-teams are listed so the division page shows the whole structure, but
# only HFR-run teams recruit through this site.
#
# Sea is provisional: the VP has not confirmed the Energy Class boat's
# sub-teams yet, so these follow the approved forum category tree.

# division: [(name, partner, recruiting, tagline), ...] in display order
STRUCTURE = {
    'land': [
        ('Data & Telemetry', '', True,
         'Live data from the car, turned into lap decisions.'),
        ('Electrical', '', True,
         'Wiring, power distribution and control systems.'),
        ('Chassis & Component', '', True,
         'The structure everything else bolts onto, and the parts that bolt onto it.'),
        ('Vehicle Dynamics', '', True,
         'Suspension, steering, braking and handling.'),
        ('Aerodynamics', '', True,
         'Shape the Shell Eco car that cuts through the air.'),
        ('HFC', '', True,
         'The hydrogen fuel cell at the heart of the car.'),
    ],
    'sea': [
        ('Cockpit & Structures', '', True,
         'The cockpit and everything we build onto the supplied hull.'),
        ('Hydrogen Systems', '', True,
         'Storage, plumbing and safety for hydrogen on the water.'),
        ('Fuel Cell & Power', '', True,
         'The fuel cell, batteries and power distribution.'),
        ('Propulsion & Performance', '', True,
         'Motor, drivetrain and propeller, tuned for the race.'),
        ('Controls & Electronics', '', True,
         "Wiring, control systems and the pilot's instruments."),
    ],
    'air': [
        ('Aerodynamics', 'UGA', False,
         'Lift, drag and surfaces for hydrogen powered flight.'),
        ('Structures', 'UGA', False,
         'A lightweight airframe that holds together.'),
        ('Avionics & Flight Operations', 'UGA', False,
         'Flight control, instrumentation and operating the aircraft.'),
        ('Propulsion', '', True,
         'Motors, propellers and the drivetrain for hydrogen flight.'),
        ('Energy Management & HFC', '', True,
         'The fuel cell, hydrogen storage and power management in the air.'),
    ],
    'operations': [
        ('Business', '', True,
         'Partnerships, events and the commercial side of HFR.'),
        ('Finance & Contracts', '', True,
         'Budgets, purchasing and agreements.'),
        # Kept so it can be switched on in admin; not on the VP's list.
        ('Creative Direction', '', False,
         'Video, posters and the identity of HFR across every channel.'),
    ],
}

# Existing rows renamed in place so any application pointing at them keeps
# its draft picks.
RENAMES = {
    'land': {'Chassis': 'Chassis & Component', 'Dynamics': 'Vehicle Dynamics'},
    'air': {'Chassis': 'Structures'},
    'operations': {'Social Media': 'Creative Direction'},
}


def apply_structure(apps, schema_editor):
    Team = apps.get_model('recruitment', 'Team')

    for division, mapping in RENAMES.items():
        for old, new in mapping.items():
            if Team.objects.filter(division=division, name=new).exists():
                continue  # already there; the old row is retired below
            Team.objects.filter(division=division, name=old).update(name=new)

    for division, teams in STRUCTURE.items():
        keep = []
        for order, (name, partner, recruiting, tagline) in enumerate(teams, start=1):
            team, _ = Team.objects.get_or_create(division=division, name=name)
            team.sort_order = order
            team.partner = partner
            team.is_recruiting = recruiting
            team.tagline = tagline
            team.save()
            keep.append(name)

        # Anything else in the division is retired. Rows an application or
        # a lead still points at are switched off rather than deleted.
        for team in Team.objects.filter(division=division).exclude(name__in=keep):
            in_use = (
                team.first_pick_applications.exists()
                or team.alternative_applications.exists()
                or team.wildcard_applications.exists()
                or team.leads.exists()
            )
            if in_use:
                team.is_recruiting = False
                team.save()
            else:
                team.delete()


class Migration(migrations.Migration):
    dependencies = [('recruitment', '0014_team_partner')]
    operations = [migrations.RunPython(apply_structure, migrations.RunPython.noop)]
