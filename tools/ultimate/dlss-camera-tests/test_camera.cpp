// SPDX-License-Identifier: MIT
#include "dlss_camera_math.h"

#include <cstdlib>
#include <cstring>
#include <iostream>

using Matrix = float[4][4];

static void Check(bool condition, const char* message) {
    if (!condition) {
        std::cerr << message << '\n';
        std::exit(1);
    }
}

static void CheckInverse(const Matrix& matrix) {
    Matrix inverse{};
    Check(bbport::dlss::InvertMatrix(inverse, matrix), "invertible camera rejected");
    for (int row = 0; row < 4; ++row)
        for (int col = 0; col < 4; ++col) {
            double left = 0.0, right = 0.0;
            for (int k = 0; k < 4; ++k) {
                left += double(matrix[row][k]) * inverse[k][col];
                right += double(inverse[row][k]) * matrix[k][col];
            }
            const double expected = row == col ? 1.0 : 0.0;
            Check(std::abs(left - expected) < 2e-5 && std::abs(right - expected) < 2e-5,
                  "camera/inverse product is not identity");
        }
    Matrix aliased;
    std::memcpy(aliased, matrix, sizeof(aliased));
    Check(bbport::dlss::InvertMatrix(aliased, aliased), "aliased inversion rejected");
    Check(std::memcmp(aliased, inverse, sizeof(aliased)) == 0, "alias changed inverse");
}

static void CheckRejected(const Matrix& matrix) {
    Matrix destination;
    for (auto& row : destination)
        for (float& value : row)
            value = 23.0f;
    Matrix before;
    std::memcpy(before, destination, sizeof(before));
    Check(!bbport::dlss::InvertMatrix(destination, matrix), "invalid matrix accepted");
    Check(std::memcmp(before, destination, sizeof(before)) == 0, "failure changed output");
}

int main() {
    // Non-zero offsets are the regression: the former perspective shortcut drops them.
    const Matrix perspective{{1.7f, 0, 0, 0}, {0, 2.1f, 0, 0},
                             {0.125f, -0.0625f, 1.0001f, 1}, {0, 0, -0.10001f, 0}};
    const Matrix orthographic{{0.5f, 0, 0, 0}, {0, 0.25f, 0, 0},
                              {0, 0, 0.01f, 0}, {-0.25f, 0.5f, -0.1f, 1}};
    const Matrix reversed_infinite{{1.7f, 0, 0, 0}, {0, 2.1f, 0, 0},
                                   {0.01f, -0.02f, 0, 1}, {0, 0, 0.1f, 0}};
    const Matrix pivot_swap{{0, 1, 0, 0}, {1, 0, 0, 0},
                            {0, 0, 1, 0}, {0, 0, 0, 1}};
    const Matrix scaled{{1e-20f, 0, 0, 0}, {0, 1e20f, 0, 0},
                        {0, 0, 1, 0}, {0, 0, 0, 1}};
    for (const Matrix* matrix : {&perspective, &orthographic, &reversed_infinite,
                                 &pivot_swap, &scaled})
        CheckInverse(*matrix);
    Matrix singular{};
    CheckRejected(singular);
    std::memcpy(singular, pivot_swap, sizeof(singular));
    std::memcpy(singular[1], singular[0], sizeof(singular[0]));
    CheckRejected(singular);
    for (float invalid : {std::numeric_limits<float>::infinity(),
                          std::numeric_limits<float>::quiet_NaN()}) {
        Matrix non_finite;
        std::memcpy(non_finite, perspective, sizeof(non_finite));
        non_finite[2][1] = invalid;
        Check(!bbport::dlss::FiniteMatrix(non_finite), "non-finite camera accepted");
        CheckRejected(non_finite);
    }
    Matrix overflow{{std::numeric_limits<float>::denorm_min(), 0, 0, 0},
                    {0, 1, 0, 0}, {0, 0, 1, 0}, {0, 0, 0, 1}};
    CheckRejected(overflow);
    std::cout << "DLSS camera: 5 projection/alias cases and 5 rejection cases passed\n";
}
