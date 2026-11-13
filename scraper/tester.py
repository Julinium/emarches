import os
import sys
# import traceback

import django

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'emarches.settings')
django.setup()

def main():
    from worker import linkify, dceify, bdcify
    # linkify()
    dceify()
    # bdcify()


if __name__ == '__main__':
    main()

