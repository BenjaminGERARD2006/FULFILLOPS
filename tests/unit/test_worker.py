from worker.retry import calculate_backoff


def test_first_retry():
    assert calculate_backoff(1) == 1


def test_second_retry():
    assert calculate_backoff(2) == 2


def test_third_retry():
    assert calculate_backoff(3) == 4


def test_retry_delay_is_capped():
    assert calculate_backoff(10) == 60
