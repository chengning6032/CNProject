from django.db import models

class AnchorBoltGeoProperties(models.Model):
    bolt_diameter = models.CharField(max_length=50, verbose_name="Bolt Diameter")
    bolt_diameter_value = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Bolt Diameter Value")
    min_root_K = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Min.Root")
    threads_per_inch = models.DecimalField(max_digits=10, decimal_places=1, null=True, blank=True, verbose_name="Threads per Inch")
    net_tensile_area_in2 = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Net Tensile Area, in2")
    net_tensile_area_cm2 = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Net Tensile Area, cm2")
    gross_bolt_area = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Gross Bolt Area")
    min_root_area = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Min Root Area")
    hex_f = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Hex F")
    heavy_hex_f = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Heavy Hex F")
    hex_abrg = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Hex,Abrg")
    heavy_hex_abrg = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Heavy Hex,Abrg")

    def __str__(self):
        return self.bolt_diameter

    class Meta:
        verbose_name = "錨栓規格"
        verbose_name_plural = "錨栓規格"

class AnchorBoltMatProperties(models.Model):
    mat_name = models.CharField(max_length=50, verbose_name="Material Name")
    unit = models.CharField(max_length=50, verbose_name="Unit")
    unitweight = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Unit Weight")
    alpha = models.DecimalField(max_digits=12, decimal_places=10, null=True, blank=True, verbose_name="Alpha")
    E = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True, verbose_name="E")
    Fy = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Fy")
    Ry = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, verbose_name="Ry")
    Fu = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Fu")
    Rt = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, verbose_name="Rt")
    rc_region = models.CharField(max_length=50, verbose_name="RC Region")


    def __str__(self):
        return self.mat_name

    class Meta:
        verbose_name = "錨栓材料規格"
        verbose_name_plural = "錨栓材料規格"

class SteelMatProperties(models.Model):
    mat_name = models.CharField(max_length=50, verbose_name="Material Name")
    unit = models.CharField(max_length=50, verbose_name="Unit")
    unitweight = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Unit Weight")
    alpha = models.DecimalField(max_digits=12, decimal_places=10, null=True, blank=True, verbose_name="Alpha")
    E = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True, verbose_name="E")
    Fy = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Fy")
    Ry = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, verbose_name="Ry")
    Fu = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Fu")
    Rt = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, verbose_name="Rt")
    rc_region = models.CharField(max_length=50, verbose_name="RC Region")


    def __str__(self):
        return self.mat_name

    class Meta:
        verbose_name = "鋼材料規格"
        verbose_name_plural = "鋼材料規格"
