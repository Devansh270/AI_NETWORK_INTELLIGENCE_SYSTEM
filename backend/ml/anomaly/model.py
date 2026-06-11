"""
ml/anomaly/model.py

LSTM Autoencoder for network traffic anomaly detection.

Architecture:
    Encoder: LSTM that reads a sequence and compresses it to a hidden state
    Decoder: LSTM that reconstructs the sequence from that hidden state

Anomaly score = mean squared reconstruction error over the sequence.
High error = the traffic pattern does not match what the model learned as "normal".
"""

import torch
import torch.nn as nn


class LSTMAutoencoder(nn.Module):
    def __init__(self, input_size: int = 5, hidden_size: int = 64, num_layers: int = 1):
        super().__init__()

        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        # Encoder: reads the input sequence, outputs a compressed representation
        self.encoder = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
        )

        # Decoder: takes the compressed state, reconstructs the sequence
        self.decoder = nn.LSTM(
            input_size=hidden_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
        )

        # Project decoder output back to original feature space
        self.output_layer = nn.Linear(hidden_size, input_size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (batch_size, seq_len, input_size)
        Returns:
            reconstructed: (batch_size, seq_len, input_size)
        """
        batch_size, seq_len, _ = x.shape

        # Encode: run input through encoder LSTM
        # encoder_output: (batch_size, seq_len, hidden_size)
        # hidden: tuple of (h_n, c_n), each (num_layers, batch_size, hidden_size)
        encoder_output, hidden = self.encoder(x)

        # Use the last encoder hidden state as the starting input for the decoder
        # Repeat the last encoder output across all time steps for decoder input
        decoder_input = encoder_output[:, -1:, :].repeat(1, seq_len, 1)

        # Decode: reconstruct the sequence
        decoder_output, _ = self.decoder(decoder_input, hidden)

        # Project to original feature space
        reconstructed = self.output_layer(decoder_output)

        return reconstructed

    def reconstruction_error(self, x: torch.Tensor) -> torch.Tensor:
        """
        Returns per-sample mean squared reconstruction error.
        Shape: (batch_size,)
        """
        reconstructed = self.forward(x)
        # MSE over all time steps and features
        error = torch.mean((x - reconstructed) ** 2, dim=(1, 2))
        return error