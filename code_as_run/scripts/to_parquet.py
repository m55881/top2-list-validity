import python_calamine as pc, pandas as pd, glob, sys
files={'v2_career':'v2/Table-S6-career-2019.xlsx','v2_single':'v2/Table-S7-singleyr-2019.xlsx',
 'v9_career':glob.glob('v9/*/Table_1_Authors_career*.xlsx')[0],'v9_single':glob.glob('v9/*/Table_1_Authors_singleyr*.xlsx')[0]}
for k,f in files.items():
    wb=pc.CalamineWorkbook.from_path(f)
    sn=[s for s in wb.sheet_names if s!='Key'][0]
    rows=wb.get_sheet_by_name(sn).to_python()
    df=pd.DataFrame(rows[1:],columns=rows[0])
    for c in df.columns:
        if df[c].dtype==object and c not in('authfull','inst_name','cntry','sm-subfield-1','sm-subfield-2','sm-field','cntry_10pct','top_cntry_career'):
            df[c]=pd.to_numeric(df[c].replace('',None),errors='coerce')
    for c in ('authfull','inst_name','cntry'): df[c]=df[c].astype(str)
    df.to_parquet(f'/home/claude/data/{k}.parquet')
    print(k,sn,df.shape, flush=True)
