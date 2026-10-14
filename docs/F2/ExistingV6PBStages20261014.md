# Existing v6 PB P/F/P stage summary

Source: `0d522be8895bf895b7548df7eeabf45679495a4d`, delivery `2797f75a641b52ddccfd84f98505b7a0e4d8ba28`. All observations below are projections of already archived ordinary synthetic business evidence. No database/body/private diagnostic is read. No new probe is run.

Phase records omit wall-clock start/end and record only calls >=0.1s; they cannot establish exact transaction wait time or align every phase with a particular fence. Such metrics remain NOT RECORDED. Failed PB run has no stage plugin; its detailed phase/heartbeat/transaction waits remain NOT RECORDED. SQLite heartbeat OperationalError durations are observed failed calls, not measurements of all transaction wait time. Nested durations overlap and must not be summed as independent elapsed time.

## v6-correction-pb

Test: `logic-correction-stage-evidence-20261014.author.test_modified_correction_matrix::test_modified_recipe_actual_cold_correction_and_independent_review[pb]`; PASS; terminal fence 3; requests 2; local tools 4.

| Public event | seconds after acceptance | remaining original 300s |
| --- | ---: | ---: |
| ACCEPTED | 0.00488734245300293 | 299.995112657547 |
| HUMAN_CORRECTION_ACCEPTED | 0.006056785583496094 | 299.9939432144165 |
| COMMAND | 42.03374195098877 | 257.96625804901123 |
| COMMAND | 49.50692844390869 | 250.4930715560913 |
| CLAIMED | 52.4519739151001 | 247.5480260848999 |
| SPEC_STEP_VERIFIED | 65.06591200828552 | 234.93408799171448 |
| WORKER_LOST | 102.55634069442749 | 197.4436593055725 |
| RECONCILED | 102.55776000022888 | 197.44223999977112 |
| CLAIMED | 105.39494347572327 | 194.60505652427673 |
| NS_RESERVED | 131.35823225975037 | 168.64176774024963 |
| MODEL_RESERVED | 131.35870695114136 | 168.64129304885864 |
| NS_RECEIVED | 141.13763284683228 | 158.86236715316772 |
| NS_SETTLED | 156.4615707397461 | 143.5384292602539 |
| SPEC_STEP_VERIFIED | 156.46323013305664 | 143.53676986694336 |
| NS_RESERVED | 189.7383165359497 | 110.2616834640503 |
| MODEL_RESERVED | 189.73980021476746 | 110.26019978523254 |
| NS_RECEIVED | 198.855895280838 | 101.14410471916199 |
| NS_SETTLED | 212.41058707237244 | 87.58941292762756 |
| SPEC_STEP_VERIFIED | 212.41170525550842 | 87.58829474449158 |
| SPEC_STEP_VERIFIED | 240.90704703330994 | 59.09295296669006 |
| SPEC_STEP_VERIFIED | 258.28904581069946 | 41.71095418930054 |
| SPEC_STEP_VERIFIED | 275.4797968864441 | 24.520203113555908 |
| STATE | 280.6401102542877 | 19.35988974571228 |
| SPEC_COMMITTED | 280.64052724838257 | 19.35947275161743 |

Accepted-to-commit: 280.64052724838257s; remaining 19.35947275161743s.

| Observed call (archive record) | seconds | status | depth |
| --- | ---: | --- | ---: |
| 43 Store.frozen_contract | 0.10193012398667634 | returned | 2 |
| 109 Store.frozen_contract | 2.576904112007469 | returned | 1 |
| 166 Store.frozen_contract | 4.120920715009561 | returned | 0 |
| 189 Store.frozen_contract | 2.578885844995966 | returned | 2 |
| 192 Store.frozen_contract | 0.1610387830005493 | returned | 5 |
| 242 Store.frozen_contract | 2.2079421450034715 | returned | 0 |
| 254 Store.frozen_contract | 2.1171932249853853 | returned | 0 |
| 284 sim2act.natural_spec_runtime.advance_model | 14.358708696992835 | returned | 4 |
| 286 Store.heartbeat | 5.017145585996332 | OperationalError:e3q8 | 0 |
| 290 Store.heartbeat | 2.3828851269790903 | returned | 3 |
| 301 sim2act.natural_spec_runtime.advance_model | 30.43073209800059 | DomainError:VERSION_CONFLICT | 4 |
| 333 Store.frozen_contract | 2.583768146985676 | returned | 6 |
| 334 sim2act.natural_spec_runtime.effective | 2.5839838169922587 | returned | 5 |
| 335 Store.heartbeat | 2.6543830430018716 | returned | 6 |
| 336 sim2act.natural_spec_runtime.renew | 2.654505407990655 | returned | 5 |
| 337 Store.heartbeat | 5.017869606002932 | OperationalError:e3q8 | 0 |
| 339 sim2act.natural_spec_runtime.reservation_check | 7.198478465987137 | returned | 6 |
| 341 Store.heartbeat | 2.4311284279974643 | returned | 6 |
| 342 sim2act.natural_spec_runtime.renew | 2.4311425710038748 | returned | 5 |
| 354 Store.heartbeat | 2.531237697985489 | returned | 6 |
| 355 sim2act.natural_spec_runtime.renew | 2.5312493160017766 | returned | 5 |
| 379 sim2act.natural_spec_runtime.advance_model | 58.816585107007995 | returned | 4 |
| 384 Store.heartbeat | 2.266129486000864 | returned | 3 |
| 396 Store.frozen_contract | 2.3324527090007905 | returned | 6 |
| 397 sim2act.natural_spec_runtime.effective | 2.33254107600078 | returned | 5 |
| 398 Store.heartbeat | 2.1494929189793766 | returned | 6 |
| 399 sim2act.natural_spec_runtime.renew | 2.149525201995857 | returned | 5 |
| 401 sim2act.natural_spec_runtime.reservation_check | 6.504607368988218 | returned | 6 |
| 403 Store.heartbeat | 2.1304877390211914 | returned | 6 |
| 404 sim2act.natural_spec_runtime.renew | 2.1308531280083116 | returned | 5 |
| 416 Store.heartbeat | 2.381941289000679 | returned | 6 |
| 417 sim2act.natural_spec_runtime.renew | 2.3819537019880954 | returned | 5 |
| 441 sim2act.natural_spec_runtime.advance_model | 58.771010870987084 | returned | 4 |
| 446 Store.heartbeat | 2.495973940996919 | returned | 3 |
| 460 sim2act.natural_spec_runtime.advance_model | 14.887306699005421 | returned | 4 |
| 465 Store.heartbeat | 2.4468069300055504 | returned | 3 |
| 479 sim2act.natural_spec_runtime.advance_model | 14.942097294988343 | returned | 4 |
| 484 Store.heartbeat | 2.541134567989502 | returned | 3 |
| 500 sim2act.natural_spec_runtime.advance_model | 19.575601755990647 | returned | 4 |

## v6-correction-pa

Test: `logic-correction-stage-evidence-20261014.author.test_modified_correction_matrix::test_modified_recipe_actual_cold_correction_and_independent_review[pb]`; FAIL; terminal fence 3; requests 2; local tools 3.

| Public event | seconds after acceptance | remaining original 300s |
| --- | ---: | ---: |
| ACCEPTED | 0.007260560989379883 | 299.9927394390106 |
| HUMAN_CORRECTION_ACCEPTED | 0.009203910827636719 | 299.99079608917236 |
| COMMAND | 45.59594774246216 | 254.40405225753784 |
| COMMAND | 56.94144582748413 | 243.05855417251587 |
| CLAIMED | 60.25776720046997 | 239.74223279953003 |
| SPEC_STEP_VERIFIED | 75.36541962623596 | 224.63458037376404 |
| NS_RESERVED | 112.91294002532959 | 187.0870599746704 |
| MODEL_RESERVED | 112.91360855102539 | 187.0863914489746 |
| NS_RECEIVED | 127.45167398452759 | 172.5483260154724 |
| NS_SETTLED | 148.85841274261475 | 151.14158725738525 |
| SPEC_STEP_VERIFIED | 148.86045479774475 | 151.13954520225525 |
| WORKER_LOST | 166.05468106269836 | 133.94531893730164 |
| RECONCILED | 166.05754494667053 | 133.94245505332947 |
| CLAIMED | 168.83787488937378 | 131.16212511062622 |
| NS_RESERVED | 198.6338608264923 | 101.36613917350769 |
| MODEL_RESERVED | 198.63680601119995 | 101.36319398880005 |
| NS_RECEIVED | 217.58281564712524 | 82.41718435287476 |
| NS_SETTLED | 232.69516134262085 | 67.30483865737915 |
| SPEC_STEP_VERIFIED | 232.6966655254364 | 67.3033344745636 |
| SPEC_STEP_VERIFIED | 261.50125885009766 | 38.498741149902344 |
| SPEC_STEP_VERIFIED | 288.22588419914246 | 11.774115800857544 |
| STATE | 307.5045621395111 | -7.504562139511108 |

| Observed call (archive record) | seconds | status | depth |
| --- | ---: | --- | ---: |
| detailed phases / heartbeat / transaction wait | NOT RECORDED | unavailable | |

## v6-correction-pb-exact

Test: `logic-correction-stage-evidence-20261014.author.test_modified_correction_matrix::test_modified_recipe_actual_cold_correction_and_independent_review[pb]`; PASS; terminal fence 3; requests 2; local tools 4.

| Public event | seconds after acceptance | remaining original 300s |
| --- | ---: | ---: |

Accepted-to-commit: 274.4787366390228s; remaining 25.521263360977173s.

| Observed call (archive record) | seconds | status | depth |
| --- | ---: | --- | ---: |
| 17 Store.frozen_contract | 0.10156407798058353 | returned | 2 |
| 18 Store.frozen_contract | 0.12023792101535946 | returned | 6 |
| 45 Store.frozen_contract | 0.18165475700516254 | returned | 2 |
| 104 Store.frozen_contract | 2.3420582710241433 | returned | 1 |
| 156 Store.frozen_contract | 2.4620583709911443 | returned | 0 |
| 170 Store.frozen_contract | 2.5872737269965 | returned | 2 |
| 217 Store.frozen_contract | 2.374524694023421 | returned | 0 |
| 229 Store.frozen_contract | 2.33790895799757 | returned | 0 |
| 257 Store.heartbeat | 5.01364523198572 | OperationalError:e3q8 | 0 |
| 260 sim2act.natural_spec_runtime.advance_model | 16.169195346999913 | returned | 4 |
| 265 Store.heartbeat | 2.5453974939882755 | returned | 3 |
| 277 Store.frozen_contract | 4.053110918001039 | returned | 6 |
| 278 sim2act.natural_spec_runtime.effective | 4.053273917990737 | returned | 5 |
| 279 Store.heartbeat | 4.043423076014733 | returned | 6 |
| 280 sim2act.natural_spec_runtime.renew | 4.04348060398479 | returned | 5 |
| 282 sim2act.natural_spec_runtime.reservation_check | 7.384400009003002 | returned | 6 |
| 284 Store.heartbeat | 2.4909072640002705 | returned | 6 |
| 285 sim2act.natural_spec_runtime.renew | 2.4909212380007375 | returned | 5 |
| 297 Store.heartbeat | 2.5226273459848017 | returned | 6 |
| 298 sim2act.natural_spec_runtime.renew | 2.522639124013949 | returned | 5 |
| 322 sim2act.natural_spec_runtime.advance_model | 69.22828662098618 | returned | 4 |
| 328 Store.heartbeat | 2.8858614210039377 | DomainError:VERSION_CONFLICT | 3 |
| 359 Store.frozen_contract | 2.6711001630173996 | returned | 6 |
| 360 sim2act.natural_spec_runtime.effective | 2.6713123630033806 | returned | 5 |
| 361 Store.heartbeat | 5.178556723025395 | OperationalError:e3q8 | 0 |
| 362 Store.heartbeat | 3.6868662199995015 | returned | 6 |
| 363 sim2act.natural_spec_runtime.renew | 3.6870809770189226 | returned | 5 |
| 365 sim2act.natural_spec_runtime.reservation_check | 8.964157707989216 | returned | 6 |
| 367 Store.heartbeat | 2.8457334130071104 | returned | 6 |
| 368 sim2act.natural_spec_runtime.renew | 2.8457492160086986 | returned | 5 |
| 380 Store.heartbeat | 2.4291231670067646 | returned | 6 |
| 381 sim2act.natural_spec_runtime.renew | 2.429132463003043 | returned | 5 |
| 405 sim2act.natural_spec_runtime.advance_model | 64.01285605298472 | returned | 4 |
| 410 Store.heartbeat | 2.8433147330069914 | returned | 3 |
| 424 sim2act.natural_spec_runtime.advance_model | 17.388946777995443 | returned | 4 |
| 429 Store.heartbeat | 2.532693223998649 | returned | 3 |
| 443 sim2act.natural_spec_runtime.advance_model | 17.242252931988332 | returned | 4 |
| 448 Store.heartbeat | 3.498643328988692 | returned | 3 |
| 464 sim2act.natural_spec_runtime.advance_model | 20.947472514002584 | returned | 4 |
