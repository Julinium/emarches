import os
import sys
# import traceback

import django

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'emarches.settings')
django.setup()

def main():
    from bonner import save_bdcs, save_results
    # save_bdcs(15)
    save_results(15)
    pass


if __name__ == '__main__':
    main()

