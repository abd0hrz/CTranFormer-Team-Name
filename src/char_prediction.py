#!/usr/bin/env python3
"""
File:   char_prediction.py
Author: Thibault Douzon
Date:   2019-09-16
        23:40:29
mail:   douzont@gmail.com
Playing with https://pytorch.org/tutorials/beginner/transformer_tutorial.html
"""

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

import math

import src.utils


class Model(nn.Module):
    def __init__(self, vocabulary_size, model_size=512, head_n=8, encoder_layers_n=6,
                 decoder_layers_n=6, feedforward_size=2048, dropout_transformer=0.1,
                 device='cpu'):
        super().__init__()
        self.vocabulary_size = vocabulary_size
        self.model_size = model_size
        self.head_n = head_n
        self.encoder_layers_n = encoder_layers_n
        self.decoder_layers_n = decoder_layers_n
        self.feedforward_size = feedforward_size
        self.dropout_transformer = dropout_transformer
        self.device = device

        self.embedding = Embedding(self.vocabulary_size, self.model_size, device=self.device)
        self.transformer = nn.modules.transformer.Transformer(d_model=self.model_size,
                                                              nhead=self.head_n,
                                                              num_encoder_layers=self.encoder_layers_n,
                                                              num_decoder_layers=self.decoder_layers_n,
                                                              dim_feedforward=self.feedforward_size,
                                                              dropout=self.dropout_transformer).to(self.device)
        self.linear = nn.Linear(self.model_size, self.vocabulary_size).to(self.device)

    def forward(self, x: torch.Tensor, y: torch.Tensor,
                x_mask: torch.Tensor = None,
                y_mask: torch.Tensor = None):

        xx = self.embedding(x)
        yy = self.embedding(y)

        if y_mask is None:
            y_mask = self.transformer.generate_square_subsequent_mask(
                y.size(0)).to(self.device)

        x_padding_mask = self._padding_mask(x)
        y_padding_mask = self._padding_mask(y)
        zz = self.transformer(xx,
                              yy,
                              src_mask=x_mask,
                              tgt_mask=y_mask,)
                              #src_key_padding_mask=x_padding_mask,
                              #tgt_key_padding_mask=y_padding_mask)
        zz = self.linear(zz)
        zz = F.log_softmax(zz, dim=-1)
        return zz.transpose(1, 0)
    
    def greedy_decode(self, x):
        max_len = 20
        ys = torch.ones(1, 1).fill_(src.utils.alphabet_d[src.utils.BEG]).to(self.device).long()
        for i in range(max_len-1):
            out = self(x, ys)
            next_word = torch.argmax(out, dim = -1)
            next_word = next_word[0][-1].detach().item()
            ys = torch.cat([ys, 
                            torch.ones(1, 1).fill_(next_word).to(self.device).long()], dim=0)
        return ys

    def _padding_mask(self, x: torch.Tensor) -> torch.ByteTensor:
        """_padding_mask [summary]

        Args:
            x (torch.Tensor): (S/T, N) input tensor

        Returns:
            torch.ByteTensor: (N, S/T) byte tensor for padding
        """
        return src.utils.get_padding_mask(x, device=self.device)


class Embedding(nn.Module):
    def __init__(self,
                 vocabulary_size: int,
                 model_size: int,
                 max_sequence_size: int = 1000,
                 device='cpu'):  # ! TODO : propagate this parameter
        super().__init__()
        self._vocabulary_size = vocabulary_size
        self._model_size = model_size
        self._max_sequence_size = max_sequence_size
        self.device = device

        self.embedding = nn.Embedding(vocabulary_size, model_size).to(self.device)
        self._register_positional_encoding()

    def _register_positional_encoding(self) -> None:
        """Computes the positional encoding

        Returns:
            None --
        """

        positional_encoding = torch.zeros(self._max_sequence_size,
                                          self._model_size)

        position = (torch.arange(
            0, self._max_sequence_size, dtype=torch.float64).view(-1, 1) *
            torch.ones(self._max_sequence_size,
                       self._model_size // 2,
                       dtype=torch.float64))

        harmonic = 10000**(
            torch.arange(0, self._model_size, 2, dtype=torch.float64) /
            self._model_size)

        positional_encoding[:, ::2] = torch.sin(position / harmonic)
        positional_encoding[:, 1::2] = torch.cos(position / harmonic)

        positional_encoding.unsqueeze_(1)
        self.register_buffer('positional_encoding', positional_encoding.to(self.device))

    def forward(self, x: torch.LongTensor) -> torch.Tensor:
        """Embedds the tensor and add positional encoding

        Arguments:
            x {torch.LongTensor} -- (S, N) tensor containing character indices

        Returns:
            torch.Tensor -- (S, N, D) embedded input
        """
        xx = self.embedding(x[:self._max_sequence_size, ...])
        xx += self.positional_encoding[:min(xx.size(0),
                                            self._max_sequence_size), ...]

        return xx


def main():
    src.utils.set_random_seed(100)
    
    device = torch.device('cuda:0')
    # device = torch.device('cpu')
    
    model = Model(10, 16, 4, 4, 4, 128, 0.1, device)
    print(model.model_size)
    v = torch.arange(0, 10).view(-1, 1).long().to(device)

    print(model.greedy_decode(v).view(-1))


if __name__ == '__main__':
    main()
