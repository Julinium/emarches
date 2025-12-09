import os, sys
import django

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'emarches.settings')
django.setup()

def main():
    from scraper import helper, bonner
    
    def handle_bdcs():
        print('\n\n\n\n======================================================')
        helper.printMessage('===', 'worker', f"▶▶▶▶▶ Now, let's do some Purchase orders ◀◀◀◀◀", 1, 1)
        # bonner.save_results(180)
        # bonner.save_bdcs(180)
        print('\n\n======================================================\n\n')
    
    handle_bdcs()


if __name__ == '__main__':
    main()
