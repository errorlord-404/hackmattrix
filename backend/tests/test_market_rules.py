from app.services.market import calculate_net_realisation


def test_net_realisation_uses_every_documented_cost():
    assert calculate_net_realisation(44000, 1500, 200, 100, 880, 300, 120) == 40900

