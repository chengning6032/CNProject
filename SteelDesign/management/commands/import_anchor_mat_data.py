import csv
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from SteelDesign.models import AnchorBoltMatProperties  # 請替換成你的 app 名稱


class Command(BaseCommand):
    help = 'Import materials from a specified CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file_path', type=str, help='The CSV file path')

    def handle(self, *args, **kwargs):
        file_path = kwargs['csv_file_path']
        self.stdout.write(self.style.SUCCESS(f'Starting to import data from {file_path}'))

        with open(file_path, 'r', encoding='utf-8') as file:
            # 使用 DictReader，它會用第一行當作 key，非常方便
            reader = csv.DictReader(file)

            for i, row in enumerate(reader):
                line_number = i + 2  # CSV 行號 (包含標頭)
                try:
                    # 清理從 CSV 讀取的值，並處理空字串
                    def clean_decimal(value):
                        if value is None or value.strip() == '':
                            return None  # 如果 model 允許 null=True，這是最好的方式
                        return Decimal(value.strip())

                    # 使用 get_or_create 避免重複匯入
                    obj, created = AnchorBoltMatProperties.objects.get_or_create(
                        mat_name=row['mat_name'].strip(),
                        defaults={
                            'unit': row['unit'].strip(),
                            'unitweight': clean_decimal(row.get('unitweight')),
                            'alpha': clean_decimal(row.get('alpha')),
                            'E': clean_decimal(row.get('E')),
                            'Fy': clean_decimal(row.get('Fy')),
                            'Ry': clean_decimal(row.get('Ry')),
                            'Fu': clean_decimal(row.get('Fu')),
                            'Rt': clean_decimal(row.get('Rt')),
                            'rc_region': row['rc_region'].strip(),
                        }
                    )
                    if created:
                        self.stdout.write(
                            self.style.SUCCESS(f'Line {line_number}: Successfully created {obj.mat_name}'))
                    else:
                        self.stdout.write(self.style.WARNING(
                            f'Line {line_number}: Material "{obj.mat_name}" already exists. Skipping creation.'))

                except (KeyError, InvalidOperation, Exception) as e:
                    # 如果出錯 (例如欄位不存在、數字格式錯誤)，印出錯誤訊息並繼續
                    self.stdout.write(self.style.ERROR(f'Error on line {line_number}: {e}'))
                    self.stdout.write(self.style.ERROR(f'Problematic row data: {row}'))
                    continue  # 繼續處理下一行

        self.stdout.write(self.style.SUCCESS('Import finished!'))