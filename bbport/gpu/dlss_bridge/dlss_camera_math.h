// SPDX-License-Identifier: MIT
#pragma once

#include <algorithm>
#include <cmath>
#include <limits>

namespace bbport::dlss {

inline bool FiniteMatrix(const float (&matrix)[4][4]) {
    for (const auto& row : matrix)
        for (float value : row)
            if (!std::isfinite(value))
                return false;
    return true;
}

// Cameras may supply off-centre, jittered, orthographic, reversed-Z or infinite-far
// projections. Invert the actual matrix rather than assuming a symmetric perspective.
// On failure leave the destination unchanged, including when it aliases the input.
inline bool InvertMatrix(float (&out)[4][4], const float (&matrix)[4][4]) {
    if (!FiniteMatrix(matrix))
        return false;
    double augmented[4][8]{};
    double scales[4]{};
    for (int row = 0; row < 4; ++row) {
        for (int col = 0; col < 4; ++col) {
            augmented[row][col] = matrix[row][col];
            scales[row] = std::max(scales[row], std::abs(augmented[row][col]));
        }
        if (scales[row] == 0.0)
            return false;
        augmented[row][row + 4] = 1.0;
    }
    for (int col = 0; col < 4; ++col) {
        int pivot = col;
        for (int row = col + 1; row < 4; ++row)
            if (std::abs(augmented[row][col]) / scales[row] >
                std::abs(augmented[pivot][col]) / scales[pivot])
                pivot = row;
        if (augmented[pivot][col] == 0.0)
            return false;
        if (pivot != col) {
            for (int entry = 0; entry < 8; ++entry)
                std::swap(augmented[pivot][entry], augmented[col][entry]);
            std::swap(scales[pivot], scales[col]);
        }
        const double divisor = augmented[col][col];
        for (double& entry : augmented[col])
            entry /= divisor;
        for (int row = 0; row < 4; ++row) {
            if (row == col)
                continue;
            const double factor = augmented[row][col];
            for (int entry = 0; entry < 8; ++entry)
                augmented[row][entry] -= factor * augmented[col][entry];
        }
    }
    float result[4][4]{};
    for (int row = 0; row < 4; ++row)
        for (int col = 0; col < 4; ++col) {
            const double value = augmented[row][col + 4];
            if (!std::isfinite(value) || std::abs(value) > std::numeric_limits<float>::max())
                return false;
            result[row][col] = static_cast<float>(value);
        }
    // Check the float matrix actually passed to NGX, in both multiplication orders.
    for (int row = 0; row < 4; ++row)
        for (int col = 0; col < 4; ++col) {
            double left = 0.0, right = 0.0;
            for (int k = 0; k < 4; ++k) {
                left += double(matrix[row][k]) * result[k][col];
                right += double(result[row][k]) * matrix[k][col];
            }
            const double expected = row == col ? 1.0 : 0.0;
            if (std::abs(left - expected) > 2e-4 || std::abs(right - expected) > 2e-4)
                return false;
        }
    for (int row = 0; row < 4; ++row)
        for (int col = 0; col < 4; ++col)
            out[row][col] = result[row][col];
    return true;
}

} // namespace bbport::dlss
