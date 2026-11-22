"""Publish an admitted compact dossier through the existing owner-profile store.

Default: dry run. Input is produced by prepare_owner_dossier from the admitted
composition, never by a public web client. Do not publish fixture-family bundles.
No source acquisition, model computation, DDL, refresh or secrets in output.
"""
import argparse,json
from pathlib import Path
from fsffl.behavioral.dossier_publication import PreparedOwnerDossier,publish_owner_dossier
from fsffl.product.behavioral_runtime import default_behavioral_store


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepared-json',required=True,type=Path)
    p.add_argument('--user-id',required=True)
    action=p.add_mutually_exclusive_group()
    action.add_argument('--publish',action='store_true')
    action.add_argument('--stage',action='store_true',help='Stage the admitted revision for the next owned refresh')
    args=p.parse_args()
    if args.prepared_json.stat().st_size>2_000_000:raise ValueError('compact dossier exceeds publication budget')
    prepared=PreparedOwnerDossier.model_validate_json(args.prepared_json.read_text())
    if not prepared.league_family_id.startswith('sleeper-family:'):
        raise ValueError('publication requires admitted production family identity')
    if args.stage:
        from datetime import datetime,UTC
        from fsffl.persistence.postgres import persistence_store_from_env
        from fsffl.behavioral.dossier_publication import dossier_artifact
        artifacts=persistence_store_from_env()
        if artifacts is None:raise ValueError('hosted artifact store is not configured')
        context=default_behavioral_store().load_runtime_context(args.user_id)
        if context is None or context['league_family_id']!=prepared.league_family_id or context['sleeper_league_external_id']!=prepared.current_provider_league_id:
            raise ValueError('staging requires matching durable user/league context')
        artifacts.put_immutable_artifact(dossier_artifact(prepared,computed_at=datetime.now(UTC)))
        print(json.dumps({'staged':True,'cases':len(prepared.cases),'resumes':len(prepared.resumes),'raw_data_printed':False}))
        return
    result=publish_owner_dossier(store=default_behavioral_store(),user_id=args.user_id,prepared=prepared,publish=args.publish)
    print(json.dumps({'published':result.published,'changed_profiles':result.changed_profiles,
        'attached_cases':result.attached_cases,'attached_resumes':result.attached_resumes,
        'skipped_future_resumes':result.skipped_future_resumes,'raw_data_printed':False}))


if __name__=='__main__':main()
