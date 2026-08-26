# Hermes Builder Hardened v3 — Release Manifest

Status: candidate installer package

Pinned implementation commit:
`28449d0e5d0a62d6008a9943cfab1e019593b150`

Expected bootstrap Git blob:
`6b57e680a2bc8c15fd60f564d30be9523cfd313f`

Installer ZIP:
`Install_Hermes_Builder_V3.zip`

ZIP SHA-256:
`de5d4ed2f91e6e9d127adced23a28239fddfb88b2ab4f3419167f60b1b476ef5`

Installer command SHA-256:
`3caf0fb54a629f8c84b5f46d9e263b4d92cd95c18586eb45e6d27034fac78b41`

README SHA-256:
`987989b11a8515e6fcf27f484f881aceb3b654bdcaded07d0de0734c9b2bada3`

Quick setup SHA-256:
`5e967325ec1dc1bc43dfdec1dbc7a3e530e155857ef032cf8d2e1047d581e7ba`

Security preconditions:
- run only from dedicated macOS Standard account `hermes-builder`;
- account must not be admin/root;
- three repository-specific deploy keys required;
- Kimi installed separately from Moonshot AI/Kimi official documentation;
- main-branch protection verified on `hermes-control`, `hermes-os-foundation`, and `avoa-quote-engine`;
- PR required, force push blocked, no builder bypass, direct main push rejected.

The package intentionally fails closed if any local precondition is not satisfied.