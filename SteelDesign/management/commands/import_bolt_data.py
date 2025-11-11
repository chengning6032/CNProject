# your_app_name/management/commands/import_bolt_data.py
import csv
from django.core.management.base import BaseCommand, CommandError
from SteelDesign.models import AnchorBoltGeoProperties

class Command(BaseCommand):
    help = 'Imports bolt specification data from a CSV file.'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='The path to the CSV file to import.')

    def handle(self, *args, **options):
        csv_file_path = options['csv_file']

        try:
            with open(csv_file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader) # Skip header row

                for i, row in enumerate(reader):
                    try:
                        # 進行類型轉換，並處理空值
                        bolt_diameter_value = float(row[1]) if row[1] else None
                        min_root = float(row[2]) if row[2] else None
                        threads_per_inch = float(row[3]) if row[3] else None
                        net_tensile_area_in2 = float(row[4]) if row[4] else None
                        net_tensile_area_cm2 = float(row[5]) if row[5] else None
                        gross_bolt_area = float(row[6]) if row[6] else None
                        min_root_area = float(row[7]) if row[7] else None
                        hex_f = float(row[8]) if row[8] else None
                        heavy_hex_f = float(row[9]) if row[9] else None
                        hex_abrg = float(row[10]) if row[10] else None
                        heavy_hex_abrg = float(row[11]) if row[11] else None

                        AnchorBoltGeoProperties.objects.create(
                            bolt_diameter=row[0],
                            bolt_diameter_value=bolt_diameter_value,
                            min_root_K=min_root,
                            threads_per_inch=threads_per_inch,
                            net_tensile_area_in2=net_tensile_area_in2,
                            net_tensile_area_cm2=net_tensile_area_cm2,
                            gross_bolt_area=gross_bolt_area,
                            min_root_area=min_root_area,
                            hex_f=hex_f,
                            heavy_hex_f=heavy_hex_f,
                            hex_abrg=hex_abrg,
                            heavy_hex_abrg=heavy_hex_abrg
                        )
                        # bolt_diameter = models.CharField(max_length=50, verbose_name="Bolt Diameter")
                        # bolt_diameter_value = models.DecimalField(max_digits=10, decimal_places=3, null=True,
                        #                                           blank=True, verbose_name="Bolt Diameter Value")
                        # min_root_K = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True,
                        #                                  verbose_name="Min.Root")
                        # threads_per_inch = models.DecimalField(max_digits=10, decimal_places=1, null=True, blank=True,
                        #                                        verbose_name="Threads per Inch")
                        # net_tensile_area_in2 = models.DecimalField(max_digits=10, decimal_places=3, null=True,
                        #                                            blank=True, verbose_name="Net Tensile Area, in2")
                        # net_tensile_area_cm2 = models.DecimalField(max_digits=10, decimal_places=3, null=True,
                        #                                            blank=True, verbose_name="Net Tensile Area, cm2")
                        # gross_bolt_area = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True,
                        #                                       verbose_name="Gross Bolt Area")
                        # min_root_area = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True,
                        #                                     verbose_name="Min Root Area")
                        # hex_f = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True,
                        #                             verbose_name="Hex F")
                        # heavy_hex_f = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True,
                        #                                   verbose_name="Heavy Hex F")
                        # hex_abrg = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True,
                        #                                verbose_name="Hex,Abrg")
                        # heavy_hex_abrg = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True,
                        #                                      verbose_name="Heavy Hex,Abrg")
                        self.stdout.write(self.style.SUCCESS(f'Successfully imported row {i+1}: {row[0]}'))
                    except ValueError as ve:
                        self.stderr.write(self.style.ERROR(f'Error converting data in row {i+1}: {row} - {ve}'))
                    except Exception as e:
                        self.stderr.write(self.style.ERROR(f'Error importing row {i+1}: {row} - {e}'))

        except FileNotFoundError:
            raise CommandError(f'File "{csv_file_path}" does not exist')
        except Exception as e:
            raise CommandError(f'Error reading CSV file: {e}')

        self.stdout.write(self.style.SUCCESS('Data import complete.'))