// Real PostGIS execution in an in-memory WASM PostgreSQL instance; no geometry mock.
import { PGlite } from '@electric-sql/pglite';
import { postgis } from '@electric-sql/pglite-postgis';
import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const root=path.dirname(fileURLToPath(import.meta.url));
const read=async name=>await readFile(path.join(root,name),'utf8');
const write=async(name,s)=>await writeFile(path.join(root,name),s);
const hash=s=>createHash('sha256').update(s).digest('hex');
const db=new PGlite({extensions:{postgis}});
await db.exec('CREATE EXTENSION IF NOT EXISTS postgis; CREATE TABLE airports(ident text PRIMARY KEY,name text,geom geometry(Point,4326));');
const airports=JSON.parse(await read('airports.json'));
for(const a of airports) await db.query('INSERT INTO airports VALUES ($1,$2,ST_SetSRID(ST_MakePoint($3,$4),4326))',[a.id,a.name,a.lon,a.lat]);
const source=await read('questions.jsonl');
const questions=source.trim().split('\n').map(JSON.parse);
if(questions.length!==240 || new Set(questions.map(q=>q.id)).size!==240) throw Error('Question count/ID invariant failed');
const answers=[];
for(const q of questions){
  const {rows}=await db.query(q.sql);
  if(rows.length!==1 || rows[0].answer===null) throw Error(`Invalid key for ${q.id}`);
  const answer=rows[0].answer;
  if(q.fixture_expected!==undefined && JSON.stringify(answer)!==JSON.stringify(q.fixture_expected)) throw Error(`Fixture assertion failed ${q.id}`);
  answers.push({id:q.id,task:q.task,answer_type:q.answer_type,answer});
}
const version=(await db.query('SELECT version() AS postgres, postgis_full_version() AS postgis')).rows[0];
await write('answer_key.jsonl',answers.map(x=>JSON.stringify(x)).join('\n')+'\n');
const quote=v=>'"'+String(v).replaceAll('"','""')+'"';
await write('ground_truth_results.csv','id,task,answer_type,answer_json,engine\n'+answers.map(x=>[x.id,x.task,x.answer_type,JSON.stringify(x.answer),'PostGIS'].map(quote).join(',')).join('\n')+'\n');
const polygon="ST_GeomFromText('POLYGON((0 0,10 0,10 10,0 10,0 0))',3857)";
const diagnostic=[];
for(const [label,wkt] of [['Interior','POINT(5 5)'],['Boundary','POINT(0 5)'],['Outside, 0.5 m','POINT(-0.5 5)'],['Outside, 2 m','POINT(-2 5)']]){
  const p=`ST_GeomFromText('${wkt}',3857)`;
  const r=(await db.query(`SELECT ST_Contains(${polygon},${p}) AS contains, ST_Covers(${polygon},${p}) AS covers, ST_Intersects(${polygon},${p}) AS intersects, ST_DWithin(${polygon},${p},1) AS within_1m`)).rows[0];
  diagnostic.push({label,wkt,...r});
}
await write('predicate_diagnostics.json',JSON.stringify(diagnostic,null,2)+'\n');
// A real-world distance example, for the figure; no wildfire represented.
const example=(await db.query(`SELECT ident,name,ST_X(geom) AS lon,ST_Y(geom) AS lat, ST_Distance(geom::geography,ST_SetSRID(ST_MakePoint(-118.3,34.1),4326)::geography) AS distance_m FROM airports ORDER BY distance_m,ident LIMIT 4`)).rows;
await write('airport_example.json',JSON.stringify(example,null,2)+'\n');
await write('run_manifest.json',JSON.stringify({engine:'PGlite with real PostGIS WASM extension',...version,node:process.version,questions:questions.length,fixture_assertions:120,questions_sha256:hash(source),answer_key_sha256:hash(await read('answer_key.jsonl')),source_subset_sha256:hash(await readFile(path.join(root,'airports_subset.csv'))),llm_status:'NOT RUN; no model accuracy claims'},null,2)+'\n');
await db.close();
console.log(`PostGIS generated ${answers.length} answers; 120 independent fixture assertions passed.`);
