"""Run from any working directory; defaults to backend/demo.db."""
import argparse
from datetime import date
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.db.session import build_engine
from app.demo.seed import seed_demo


def main():
    parser=argparse.ArgumentParser(description='Generate deterministic demo data in a dedicated SQLite database')
    parser.add_argument('--database',type=Path,default=Path(__file__).resolve().parents[1]/'demo.db')
    parser.add_argument('--seed',type=int,default=42)
    parser.add_argument('--start-date',type=date.fromisoformat,default=date(2026,1,1))
    parser.add_argument('--days',type=int,default=90)
    args=parser.parse_args()
    target=args.database.resolve()
    if not target.name.endswith('.demo.db') and target.name!='demo.db':
        parser.error('database filename must be demo.db or end with .demo.db')
    engine=build_engine('sqlite:///'+target.as_posix())
    try:
        print(seed_demo(engine,args.seed,args.start_date,args.days))
        print(f'Demo database: {target}')
    finally: engine.dispose()

if __name__=='__main__': main()
