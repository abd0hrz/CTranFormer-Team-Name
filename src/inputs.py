#!/usr/bin/env python3
"""
File:   inputs.py
Author: Thibault Douzon
Date:   2019-09-16
        23:40:21
mail:   douzont@gmail.com
"""
import pathlib

import torch
import torch.utils.data as data
import numpy as np

import src.utils

from typing import Dict


class DemoDataset:
    def __init__(self, vocab_size, size):
        super().__init__()
        self.vocab_size = vocab_size
        self.size = size
        self.len_seq = 10
        self.data = np.random.randint(6, self.vocab_size - 1,
                                      size=(size, self.len_seq),
                                      dtype=np.int64)

    def __getitem__(self, key):
        if 0 <= key < self.size:
            return self.data[key, :]
        else:
            raise IndexError

    def __len__(self):
        return len(self.data)


class DemoLoader:
    def __init__(self, dataset, batch_size, device='cpu'):
        super().__init__()
        self._dataset = dataset
        self.batch_size = batch_size
        self.device = device

        self._sampler = data.BatchSampler(data.RandomSampler(
            self._dataset,
            replacement=False),
            self.batch_size, False)

    def __iter__(self):
        for next_batch in self._sampler:
            next_input = torch.zeros(self._dataset.len_seq,
                                     self.batch_size).to(self.device,
                                                         dtype=torch.int64)
            next_target = torch.zeros(self._dataset.len_seq+1,
                                      self.batch_size).to(self.device,
                                                          dtype=torch.int64)
            next_output = torch.ones(self._dataset.len_seq+1,
                                     self.batch_size).to(self.device,
                                                         dtype=torch.int64)

            for i, item_idx in enumerate(next_batch):
                tensor = torch.from_numpy(self._dataset[item_idx])
                next_input[:, i] = tensor
                next_target[1:, i] = next_input[:, i] + 1
                next_output[:-1, i] = next_input[:, i] + 1

            yield next_input, next_target, next_output

    def __len__(self):
        return self._dataset.__len__()


class TeamNameDataset(data.Dataset):
    def __init__(self,
                 path: pathlib.Path,
                 vocabulary: Dict[str, int] = src.utils.alphabet_d):
        super().__init__()
        self.path = path
        self.vocabulary = vocabulary
        self._data = list(src.utils.get_team_names(path))

    def __len__(self):
        return len(self._data)

    def __getitem__(self, key: int):
        if 0 <= key < len(self._data):
            return src.utils.vectorize(self._data[key], self.vocabulary)
        else:
            raise IndexError


class TeamNameLoader:
    def __init__(self,
                 dataset: data.Dataset,
                 mask: bool,
                 batch_size: int,
                 drop_last: bool = False,
                 device='cpu'):
        super().__init__()
        self._dataset = dataset
        self.mask = mask
        self.batch_size = batch_size
        self.drop_last = drop_last
        self.device = device

        # * TODO: A better than random sampler that take into account sample length
        self._sampler = data.BatchSampler(data.RandomSampler(
            self._dataset, replacement=False),
            batch_size=self.batch_size,
            drop_last=self.drop_last)

    def __iter__(self):
        # * IDEA add temperature level to control no of masks
        beg_item = self._dataset.vocabulary[src.utils.BEG]
        end_item = self._dataset.vocabulary[src.utils.END]
        pad_item = self._dataset.vocabulary[src.utils.PAD]
        msk_item = self._dataset.vocabulary[src.utils.MSK]
        for next_batch in self._sampler:
            max_seq_len = max(len(self._dataset[i]) for i in next_batch)
            next_input = torch.ones(max_seq_len,
                                    self.batch_size,
                                    dtype=torch.int64).fill_(pad_item)

            next_target = torch.ones(max_seq_len + 1,
                                     self.batch_size,
                                     dtype=torch.int64).fill_(pad_item)
            next_target[0, :] = beg_item

            next_output = torch.ones(max_seq_len + 1,
                                     self.batch_size,
                                     dtype=torch.int64).fill_(pad_item)

            # ? If too much memory is used, merge output and target and move
            # ? further processing to the training loop
            for i, tensor_idx in enumerate(next_batch):
                tensor = torch.Tensor(self._dataset[tensor_idx])
                next_input[:len(tensor), i] = tensor

                next_target[1:len(tensor) + 1, i] = tensor

                next_output[:len(tensor), i] = tensor
                next_output[len(tensor), i] = end_item
                if self.mask:
                    rnd_mask_idx = torch.randint(len(tensor), (1, ))
                    next_input[rnd_mask_idx, i] = msk_item

            yield (next_input.to(self.device), next_target.to(self.device),
                   next_output.to(self.device))

    def __len__(self):
        return self._dataset.__len__()


def get_dataset(path: pathlib.Path,
                mask: bool,
                batch_size: int,
                shuffle: bool = True,
                drop_last: bool = False,
                device='cpu'):
    dataset = TeamNameDataset(path)
    return TeamNameLoader(dataset,
                          mask=mask,
                          batch_size=batch_size,
                          drop_last=drop_last,
                          device=device)


def main():
    # p = pathlib.Path("ctftime_team_names.txt")
    # dataset = TeamNameDataset(p)
    # dataloader = TeamNameLoader(dataset, True, 2)

    dataset = DemoDataset(10, 100)
    dataloader = DemoLoader(dataset, 3, 'cpu')
    for i, d in enumerate(dataloader):
        if i > 0:
            break

        print(d)


if __name__ == '__main__':
    main()
