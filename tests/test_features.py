"""Feature-level tests: the locked parket / balance definitions."""

from censorzero.features import compute_features


def test_single_official_source_is_parket():
    f = compute_features(
        "Шмигаль анонсував нову програму",
        "Прем'єр-міністр Денис Шмигаль заявив, що уряд запускає програму.",
    )
    assert f.official_focus
    assert f.oc == 1 and f.nc == 0 and f.sc == 1
    assert f.parket and f.balance_risk


def test_official_plus_expert_is_not_parket():
    f = compute_features(
        "Шмигаль анонсував програму",
        "Прем'єр-міністр Денис Шмигаль заявив про програму. "
        "Однак економіст Іван Петренко зауважив, що бракує фінансування.",
    )
    assert f.oc >= 1 and f.nc >= 1
    assert not f.parket  # a non-official voice is present


def test_zero_sources_is_never_parket():
    f = compute_features(
        "Битва за Україну. День шістсот двадцять другий",
        "Ми зібрали інформацію про перебіг бойових дій за минулу добу.",
    )
    assert f.sc == 0
    assert not f.parket


def test_foreign_official_single_source_is_not_parket():
    f = compute_features(
        "Столтенберг зробив заяву",
        "Генсек НАТО Єнс Столтенберг заявив, що Альянс підтримує Україну.",
    )
    assert f.fc >= 1
    assert f.oc == 0
    assert not f.parket  # foreign officialdom is excluded by definition


def test_balance_is_superset_of_parket():
    # Two Ukrainian officials, no other voices -> balance_risk but not parket
    # (parket requires exactly one source).
    f = compute_features(
        "Зеленський і Шмигаль обговорили бюджет",
        "Президент Володимир Зеленський заявив про пріоритети. "
        "Прем'єр Денис Шмигаль додав, що бюджет збалансований.",
    )
    assert f.oc == 2 and f.nc == 0
    assert f.balance_risk and not f.parket
