from typing import List, Tuple, NamedTuple

import labels
import sampling
from backend import ImageSlice
from model import LabelSession
from sessions import LabelSessionType


class ComparisonRankResult(NamedTuple):
    score: int
    win_count: int
    loss_count: int
    draw_count: int
    total_count: int


def rank_slices(label_session: LabelSession) -> List[Tuple[ImageSlice, ComparisonRankResult]]:
    assert label_session.session_type == LabelSessionType.COMPARISON_SLICE.name

    rank_data = {sl: [0, 0, 0, 0, 0] for sl in sampling.get_slices_from_session(label_session)}

    for el, el_labels in labels.get_all_labels(label_session).items():
        if len(el_labels) == 0:
            continue
        comparison = sampling.get_comparison_from_element(el)
        latest_label = el_labels[-1].label_value

        data1 = rank_data[comparison[0]]
        data2 = rank_data[comparison[1]]

        # total_count
        data1[4] += 1
        data2[4] += 1

        if latest_label == 'First':
            data1[0] += 1  # score
            data2[0] -= 1  # score

            data1[1] += 1  # win_count
            data2[2] += 1  # loss_count
        elif latest_label == 'Second':
            data2[0] += 1  # score
            data1[0] -= 1  # score

            data2[1] += 1  # win_count
            data1[2] += 1  # loss_count
        else:
            data1[3] += 1  # draw_count
            data2[3] += 1  # draw_count

    return sorted(
        [(sl, ComparisonRankResult(d[0], d[1], d[2], d[3], d[4])) for sl, d in rank_data.items()],
        key=lambda t: t[1].score, reverse=True
    )
