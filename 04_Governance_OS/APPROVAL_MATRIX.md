# Approval Matrix

| Change | Hermes may coordinate | Builder may implement | Claude review | Amjad approval |
|---|---|---|---|---|
| Documentation | Yes | Yes | Optional | Optional |
| Presentation-only | Yes | Yes | Recommended | Required for visible acceptance |
| Interaction or bug fix | Yes | Yes | Required | Required before merge |
| Business logic | Yes | Yes | Required | Explicit |
| Pricing or commercial calculation | Yes | Yes under strict contract | Required | Explicit final approval |
| Database migration | Yes | Yes under migration plan | Required | Explicit |
| Security/permissions | Yes | Yes under security plan | Required | Explicit |
| Production deploy | Coordinate only | No | Evidence review | Required initially |
| Destructive production data change | No autonomous action | No | Required | Explicit per action |
