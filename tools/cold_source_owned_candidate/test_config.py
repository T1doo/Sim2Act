"""Private test configuration, not an admission or production code witness."""
def config():
 from sim2act import production_trial_policy as p, production_trial_sender as sender, natural_spec_runtime as rt
 from sim2act.natural_source_archives import BodyArchive
 from sqlalchemy.engine import RowMapping
 from sim2act.contracts import Limits
 def descriptor(cls,name):
  return next(vars(base)[name] for base in cls.__mro__ if name in vars(base))
 models=tuple((c,c.__module__+'.'+c.__qualname__,*(descriptor(c,k) for k in ('__dict__','__pydantic_fields_set__','__pydantic_extra__','__pydantic_private__'))) for c in (p.Slot,p.ReservationIdentity,p.Outcome,sender.Capture,BodyArchive))
 return (models,RowMapping,tuple(descriptor(RowMapping,k) for k in ('_parent','_data','_key_to_index')),
  tuple((c,descriptor(c,'_keys')) for c in (rt._ColdGraphCursorMeta,rt._ColdGraphSimpleMeta)),rt._ColdGraphQuotedName,(Limits,descriptor(Limits,'__dict__'),next(v for v in rt._cold_graph_limit_values.__code__.co_consts if type(v) is tuple and v==('max_requests','max_tools','max_repairs','max_total_tokens','max_output_tokens','run_seconds'))))
