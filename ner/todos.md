# Entity cleanup todos
1. Fold `Provider-Role` and `Provider-Type` under `Provider`
2. Fold `*-Code` entities under single `Code`
3. Fold `Encounter-Type` under `Encounter`
4. Rename `Observation-Specimen` to `Specimen`
5. Drop `Contraindication` and make `Contraindicates` a direct relation
6. Drop `Temporal-Connection` and make `Arg` into `Before`/`During`/`After`
7. Drop `And` and `Or` and make into `Relations`