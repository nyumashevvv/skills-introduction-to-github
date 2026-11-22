#!/usr/bin/env python3
"""Downloads Overture Maps data for Koh Samui (anonymous S3 access via DuckDB).

buildings.parquet  - all footprints: OpenStreetMap + Google Open Buildings + Microsoft ML Buildings
roads_extra.parquet - road segments that come from sources other than OSM (e.g. TomTom)

  python3 tools/fetch_overture.py raw/overture [release]
"""
import os, sys
import duckdb

out = sys.argv[1] if len(sys.argv) > 1 else "overture"
release = sys.argv[2] if len(sys.argv) > 2 else "2026-11-18.0"
os.makedirs(out, exist_ok=True)
os.environ.pop("AWS_ACCESS_KEY_ID", None)
os.environ.pop("AWS_SECRET_ACCESS_KEY", None)
con = duckdb.connect()
con.execute("INSTALL httpfs; LOAD httpfs; SET s3_region='us-west-2'; SET s3_access_key_id=''; SET s3_secret_access_key='';")
R = f"s3://overturemaps-us-west-2/release/{release}"
bb = "bbox.xmin>99.90 AND bbox.xmax<100.11 AND bbox.ymin>9.39 AND bbox.ymax<9.60"
con.execute(f"""COPY (SELECT id, geometry, height, num_floors, class, subtype, sources[1].dataset AS src
  FROM read_parquet('{R}/theme=buildings/type=building/*', hive_partitioning=1) WHERE {bb})
  TO '{out}/buildings.parquet' (FORMAT parquet)""")
con.execute(f"""COPY (SELECT id, geometry, class
  FROM read_parquet('{R}/theme=transportation/type=segment/*', hive_partitioning=1)
  WHERE {bb} AND subtype='road' AND len(list_filter(sources, lambda s: s.dataset='OpenStreetMap'))=0)
  TO '{out}/roads_extra.parquet' (FORMAT parquet)""")
print(con.execute(f"SELECT src, count(*) FROM '{out}/buildings.parquet' GROUP BY 1").fetchall())
