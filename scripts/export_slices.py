import os
from argparse import ArgumentParser

import backend
import sampling
import sessions
from sessions import LabelSessionType
from application import application
from model import db

EXPORTED_SLICES_DIR_PATH = 'exported_slices'


def inc_dir_name(path: str) -> str:
    new_path = path

    i = 1
    while os.path.exists(new_path):
        new_path = path + ' {}'.format(i)
        i += 1

    return new_path


def export_slices(session_id: int):
    with application.app_context():
        label_session = sessions.get_session_by_id(db.session, session_id)
        if label_session is None:
            print('Session with id {} not found'.format(session_id))
            return

        session_slices_dir_path = os.path.join(EXPORTED_SLICES_DIR_PATH, label_session.session_name + ' Slices')
        session_slices_dir_path = inc_dir_name(session_slices_dir_path)

        os.makedirs(session_slices_dir_path, exist_ok=True)

        slices = sampling.get_slices_from_session(label_session)
        dataset = backend.get_dataset(label_session.dataset)

        for sl in slices:
            d_img = backend.get_image(dataset, sl.image_name)
            sl_max = backend.get_image_info(d_img)[1]
            sl_img = backend.get_slice(d_img, sl.slice_index, sl.slice_type, 0, sl_max)

            save_name = '{}_{}_{}.png'.format(sl.image_name, sl.slice_type.name, sl.slice_index)
            save_path = os.path.join(session_slices_dir_path, save_name)

            sl_img.save(save_path)
            print('Saved {}'.format(save_path))


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('session_id', type=int)

    args = parser.parse_args()

    export_slices(args.session_id)
