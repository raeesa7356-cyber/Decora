from django.db import migrations


def backfill_orderitem_combinations(apps, schema_editor):
    OrderItem = apps.get_model('admin_orders', 'OrderItem')
    VariantCombination = apps.get_model('catalog', 'VariantCombination')

    for item in OrderItem.objects.all():
        old_variant_id = item.variant_id  # still readable before the column is dropped
        if not old_variant_id:
            continue

        combo = VariantCombination.objects.filter(
            product_id=item.product_id,
            variants__id=old_variant_id
        ).first()  # best-effort: old orders never recorded the exact combo

        if combo:
            item.combination_id = combo.id
            item.save(update_fields=['combination_id'])


def reverse_backfill(apps, schema_editor):
    OrderItem = apps.get_model('admin_orders', 'OrderItem')
    OrderItem.objects.update(combination_id=None)


class Migration(migrations.Migration):

    dependencies = [
    ('admin_orders', '0011_orderitem_combination_alter_orderitem_variant'),
]

    operations = [
        migrations.RunPython(backfill_orderitem_combinations, reverse_backfill),
    ]