"""Deterministic, public-data-only financial-audit environment."""
from __future__ import annotations
import ast, copy, csv, hashlib, json, random
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
from typing import Any, Dict, List, Tuple

PUBLIC_TABLES = ("ledger", "invoices", "payments", "fx")

def _id(prefix: str, rng: random.Random) -> str:
    return f"{prefix}_{rng.randrange(10**8):08x}"

def _safe_math(expression: str) -> str:
    if len(expression) > 100: raise ValueError("expression is too long")
    node = ast.parse(expression, mode="eval")
    def visit(n):
        if isinstance(n, ast.Expression): return visit(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)): return Decimal(str(n.value))
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
            return -visit(n.operand) if isinstance(n.op, ast.USub) else visit(n.operand)
        if isinstance(n, ast.BinOp) and type(n.op) in (ast.Add, ast.Sub, ast.Mult, ast.Div):
            a,b=visit(n.left),visit(n.right)
            return {ast.Add:a+b, ast.Sub:a-b, ast.Mult:a*b, ast.Div:a/b}[type(n.op)]
        raise ValueError("only arithmetic numbers are allowed")
    return str(visit(node))

@dataclass
class Episode:
    public: Dict[str, Any]
    truth: List[Dict[str, Any]]
    provenance: List[Dict[str, Any]]

class FinancialAuditEnv:
    """A compact Gymnasium-style environment; no gym dependency is needed."""
    def __init__(self, config: Dict[str, Any] | None = None):
        self.config = config or {}; self.max_steps = min(int(self.config.get("max_steps",100)),100)
        self.current_step=0; self.terminated=False; self.truncated=False; self.episode=None

    def reset(self, seed: int | None = None, config: Dict[str, Any] | None = None) -> Tuple[Dict[str,Any],Dict[str,Any]]:
        if config: self.config.update(config); self.max_steps=min(int(self.config.get("max_steps",100)),100)
        self.current_step=0; self.terminated=self.truncated=False
        self.episode=self._generate(0 if seed is None else seed)
        p=self.episode.public
        return {"task":"Audit the company records and submit evidence-backed findings.","manifest":copy.deepcopy(p["manifest"]),"policy":copy.deepcopy(p["policy"]),"remaining_budget_steps":self.max_steps}, {"episode_id":p["manifest"]["episode_id"]}

    def _generate(self, seed: int) -> Episode:
        r=random.Random(seed); eid=f"ep_{seed:08x}"; rows=[]; invoices=[]; payments=[]; truth=[]; provenance=[]
        def add_invoice(amount, currency="USD", issued="2026-01-05T10:00:00+00:00", due="2026-01-20T00:00:00+00:00"):
            inv=_id("inv",r); entity=_id("ent",r); invoices.append({"doc_id":_id("doc",r),"invoice_id":inv,"entity_id":entity,"issued_at":issued,"due_at":due,"currency":currency,"total_minor":amount,"line_items":[{"description":"Services","amount_minor":amount}]}); return inv,entity
        def row(account,debit,credit,currency,inv=None,pay=None,ts="2026-01-06T12:00:00+00:00"):
            rid=_id("r",r); rows.append({"row_id":rid,"timestamp":ts,"account":account,"debit_minor":debit,"credit_minor":credit,"currency":currency,"entity_id":None,"invoice_id":inv,"payment_id":pay}); return rid
        # Correct invoice and settlement provide realistic context.
        good,_=add_invoice(12000); row("1200",12000,0,"USD",good); row("4100",0,12000,"USD",good)
        # 1: duplicate invoice booking
        inv,_=add_invoice(15000); a=row("1200",15000,0,"USD",inv); b=row("1200",15000,0,"USD",inv,ts="2026-01-07T12:00:00+00:00")
        truth.append({"issue_id":"iss_dup","type":"duplicate_invoice","affected_ids":sorted([a,b]),"expected_amount_minor":15000,"currency":"USD","allowed_evidence_sets":[sorted([a,b])]}); provenance.append({"issue_id":"iss_dup","change":"duplicated receivable posting"})
        # 2: invoice paid partly but allocation is missing
        inv2,_=add_invoice(20000); row("1200",20000,0,"USD",inv2); pay=_id("pay",r); payments.append({"doc_id":_id("doc",r),"payment_id":pay,"timestamp":"2026-01-18T09:00:00+00:00","currency":"USD","amount_minor":8000,"invoice_refs":[]}); p=row("1010",8000,0,"USD",None,pay)
        truth.append({"issue_id":"iss_alloc","type":"missing_payment_allocation","affected_ids":sorted([inv2,pay,p]),"expected_amount_minor":8000,"currency":"USD","allowed_evidence_sets":[sorted([inv2,pay,p])]}); provenance.append({"issue_id":"iss_alloc","change":"removed payment allocation"})
        # 3: wrong date/fx: EUR settlement booked at current rate rather than payment date rate
        inv3,_=add_invoice(10000,"EUR","2026-01-28T10:00:00+00:00"); row("1200",10000,0,"EUR",inv3); pay2=_id("pay",r); payments.append({"doc_id":_id("doc",r),"payment_id":pay2,"timestamp":"2026-01-31T23:30:00+00:00","currency":"EUR","amount_minor":10000,"invoice_refs":[inv3]}); fxrow=row("1010",12000,0,"USD",None,pay2,"2026-01-31T23:30:00+00:00")
        truth.append({"issue_id":"iss_fx","type":"fx_rate_date_mismatch","affected_ids":sorted([pay2,fxrow]),"expected_amount_minor":11000,"currency":"USD","allowed_evidence_sets":[sorted([pay2,fxrow])]}); provenance.append({"issue_id":"iss_fx","change":"used 1.20 instead of 1.10 payment-date FX rate"})
        # 4: period cutoff posting
        inv4,_=add_invoice(5000,"USD","2026-02-01T00:05:00+00:00"); cutoff=row("4100",0,5000,"USD",inv4,"", "2026-01-31T23:55:00+00:00")
        truth.append({"issue_id":"iss_period","type":"wrong_reporting_period","affected_ids":sorted([inv4,cutoff]),"expected_amount_minor":5000,"currency":"USD","allowed_evidence_sets":[sorted([inv4,cutoff])]}); provenance.append({"issue_id":"iss_period","change":"posted February invoice in January"})
        # clean decoy: same value but distinct invoice, valid FX item
        decoy,_=add_invoice(15000); row("1200",15000,0,"USD",decoy); row("4100",0,15000,"USD",decoy)
        r.shuffle(rows); r.shuffle(invoices); r.shuffle(payments)
        manifest={"schema_version":"1.0","episode_id":eid,"base_currency":"USD","period_start":"2026-01-01T00:00:00+00:00","period_end":"2026-01-31T23:59:59+00:00","timezone":"UTC","total_records":len(rows),"total_documents":len(invoices)+len(payments),"rounding":"round_half_even"}
        policy={"fx_date":"payment_timestamp","period":"inclusive UTC January 2026","minor_units":{"USD":2,"EUR":2},"rounding":"round_half_even"}
        public={"manifest":manifest,"ledger":rows,"invoices":invoices,"payments":payments,"fx":[{"date":"2026-01-31","source_currency":"EUR","target_currency":"USD","rate":"1.10"},{"date":"2026-02-01","source_currency":"EUR","target_currency":"USD","rate":"1.20"}],"policy":policy}
        return Episode(public,truth,provenance)

    def step(self, action: Dict[str,Any]):
        if self.episode is None: raise RuntimeError("Call reset() first.")
        if self.terminated or self.truncated: raise RuntimeError("Episode is already finished. Call reset() first.")
        self.current_step+=1
        if self.current_step>self.max_steps: self.truncated=True; return {"error":"Step limit reached"},0.0,False,True,{"remaining_steps":0}
        typ=action.get("type"); obs={}; reward=0.0; p=self.episode.public
        if typ=="list_records":
            table=action.get("table","ledger"); cursor=action.get("cursor",0); limit=action.get("limit",50)
            if table not in PUBLIC_TABLES or not isinstance(cursor,int) or not isinstance(limit,int): obs={"error":"invalid table, cursor or limit"}
            else:
                limit=max(1,min(limit,50)); records=p[table][cursor:cursor+limit]; obs={"table":table,"records":copy.deepcopy(records),"next_cursor":cursor+limit if cursor+limit<len(p[table]) else None}
        elif typ=="get_record":
            table=action.get("table","ledger"); key={"ledger":"row_id","invoices":"invoice_id","payments":"payment_id","fx":"date"}.get(table); found=next((x for x in p.get(table,[]) if key and x.get(key)==action.get("id")),None); obs={"record":copy.deepcopy(found)} if found else {"error":"record not found"}
        elif typ=="get_document":
            found=next((x for t in ("invoices","payments") for x in p[t] if x["doc_id"]==action.get("doc_id")),None); obs={"document":copy.deepcopy(found)} if found else {"error":"document not found"}
        elif typ=="calculator":
            try: obs={"result":_safe_math(str(action.get("expression","")))}
            except (ValueError,InvalidOperation,ZeroDivisionError,SyntaxError): obs={"error":"invalid arithmetic expression"}
        elif typ=="submit":
            self.terminated=True; findings=action.get("findings",[])
            if not isinstance(findings,list) or len(findings)>30: obs={"status":"error","message":"invalid findings"}; reward=-1.0
            else: reward=self._reward(findings); obs={"status":"submitted","reward":reward}
        else: obs={"error":"unknown action"}
        return obs,reward,self.terminated,self.truncated,{"remaining_steps":max(0,self.max_steps-self.current_step)}

    def _reward(self, findings):
        matched=set(); tp=fp=0
        for f in findings:
            ids=set(f.get("affected_ids",[])); evidence=set(f.get("evidence_ids",[])); hit=None
            for i,t in enumerate(self.episode.truth):
                if i not in matched and f.get("type")==t["type"] and ids==set(t["affected_ids"]) and f.get("currency")==t["currency"] and f.get("claimed_amount_minor")==t["expected_amount_minor"] and any(evidence==set(x) for x in t["allowed_evidence_sets"]): hit=i; break
            if hit is None: fp+=1
            else: matched.add(hit); tp+=1
        fn=len(self.episode.truth)-tp; d=2*tp+fp+fn; f1=2*tp/d if d else 1.0
        return max(-1.0,min(1.0,2*f1-1-0.002*self.current_step))

    def export_episode(self) -> Dict[str,str]:
        """Serializations for organizers; caller decides where secret files live."""
        if self.episode is None: raise RuntimeError("Call reset() first.")
        p=self.episode.public; out={k:json.dumps(p[k],ensure_ascii=False,indent=2) for k in ("manifest","policy")}
        for name in ("invoices","payments"): out[name+".jsonl"]="\n".join(json.dumps(x,ensure_ascii=False) for x in p[name])+"\n"
        for name in ("ledger","fx"):
            keys=list(p[name][0]) if p[name] else []; import io; s=io.StringIO(); w=csv.DictWriter(s,fieldnames=keys); w.writeheader(); w.writerows(p[name]); out[name+".csv"]=s.getvalue()
        out["truth.json"]=json.dumps(self.episode.truth,ensure_ascii=False,indent=2); out["provenance.json"]=json.dumps(self.episode.provenance,ensure_ascii=False,indent=2)
        return out
