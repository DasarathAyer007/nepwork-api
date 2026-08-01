from django.db import migrations


def remove_admin_roles_edit(apps, schema_editor):
    RolePermission = apps.get_model("users", "RolePermission")

    RolePermission.objects.filter(
        role__code="admin", permission__code="roles.edit"
    ).delete()


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0008_role_permission_system"),
    ]

    operations = [
        migrations.RunPython(remove_admin_roles_edit, noop_reverse),
    ]
