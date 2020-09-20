from scripts.fanduel_lineup_creator import *

csv_path = 'test_contest/test_contest.csv'

contest_df = format_contest_csv(csv_path)

pgs,sgs,sfs,pfs,cs = get_predictions(contest_df)

optimized_lineup = get_optimized_lineup(pgs,sgs,sfs,pfs,cs)

print(optimized_lineup)