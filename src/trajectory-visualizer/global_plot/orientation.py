import numpy as np


def quaternion_to_matrix(
    x: float,
    y: float,
    z: float,
    w: float,
) -> np.ndarray:
    """Convert an [x, y, z, w] quaternion to an active rotation matrix."""

    # Store the quaternion components in a NumPy array.
    quaternion = np.array([x, y, z, w], dtype=float)

    # Reject missing or infinite values.
    if not np.isfinite(quaternion).all():
        raise ValueError("Quaternion components must be finite.")

    # Rescale first to avoid overflow when calculating the norm.
    scale = np.max(np.abs(quaternion))

    if scale == 0:
        raise ValueError("A zero quaternion cannot represent a rotation.")

    quaternion = quaternion / scale

    # Normalize the quaternion to unit length.
    quaternion = quaternion / np.linalg.norm(quaternion)

    x, y, z, w = quaternion

    # Build the rotation matrix from the normalized components.
    rotation = np.array(
        [
            [
                1 - 2 * (y * y + z * z),
                2 * (x * y - z * w),
                2 * (x * z + y * w),
            ],
            [
                2 * (x * y + z * w),
                1 - 2 * (x * x + z * z),
                2 * (y * z - x * w),
            ],
            [
                2 * (x * z - y * w),
                2 * (y * z + x * w),
                1 - 2 * (x * x + y * y),
            ],
        ],
        dtype=float,
    )

    return rotation

def check_rotation_matrix(rotation: np.ndarray) -> dict:
    """Check orthogonality and determinant without rounding the matrix."""

    # A rotation matrix must have three rows and three columns.
    if rotation.shape != (3, 3):
        raise ValueError("Expected a 3x3 matrix.")

    identity = np.eye(3)

    # Compare R transpose multiplied by R with the identity matrix.
    orthogonal = np.allclose(
        rotation.T @ rotation,
        identity,
        atol=1e-10,
        rtol=0,
    )

    # A proper rotation has determinant +1.
    determinant = float(np.linalg.det(rotation))

    valid = orthogonal and np.isclose(
        determinant,
        1.0,
        atol=1e-10,
        rtol=0,
    )

    return {
        "orthogonal": bool(orthogonal),
        "determinant": determinant,
        "valid": bool(valid),
    }

# Test Library
if __name__ == "__main__":
    # A 90-degree rotation around the positive Z axis.
    rotation = quaternion_to_matrix(0.0, 0.0, 1.0, 1.0)

    # Rotate a vector initially aligned with the X axis.
    vector = np.array([1.0, 0.0, 0.0])
    rotated_vector = rotation @ vector

    print("Rotation matrix:")
    print(np.round(rotation, 6))

    print("\nRotated vector:")
    print(np.round(rotated_vector, 6))

    print("\nValidation:")
    print(check_rotation_matrix(rotation))