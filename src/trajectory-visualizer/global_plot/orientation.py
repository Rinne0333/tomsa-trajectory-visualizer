import numpy as np


# Convert quaternion components to a rotation matrix
def quaternion_to_matrix(
    x: float,
    y: float,
    z: float,
    w: float,
) -> np.ndarray:
    """Convert an [x, y, z, w] quaternion to an active rotation matrix."""

    # Store the quaternion components in a NumPy array
    quaternion = np.array([x, y, z, w], dtype=float)

    # Reject missing (NaN) or infinite values
    if not np.isfinite(quaternion).all():
        raise ValueError("Quaternion components must be finite.")

    # Find the biggest value in the quaternion to avoid numerical issues when normalizing
    scale = np.max(np.abs(quaternion))

    # Reject a quaternion with all components equal to zero
    if scale == 0:
        raise ValueError("A zero quaternion cannot represent a rotation.")

    # Rescale the quaternion to avoid numerical issues when normalizing
    quaternion = quaternion / scale

    # Normalize the quaternion to unit length.
    quaternion = quaternion / np.linalg.norm(quaternion)

    # Extract the normalized quaternion components for the matrix formula
    x, y, z, w = quaternion

    # Build the rotation matrix from the normalized components
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

    # Return the rotation matrix as a 3x3 NumPy array
    return rotation

# Check wether a 3x3 matrix represents a poper rotation 
def check_rotation_matrix(rotation: np.ndarray) -> dict:
    """Check orthogonality and determinant without rounding the matrix."""

    # Rejects matrixes that are not 3x3
    if rotation.shape != (3, 3):
        raise ValueError("Expected a 3x3 matrix.")

    # Creae a 3x3 identity mtrix
    identity = np.eye(3)

    # Check whether R transpose multiplied by R is approximately identity
    orthogonal = np.allclose(
        rotation.T @ rotation,
        identity,
        atol=1e-10,
        rtol=0,
    )

    # Calculate the determinant: A proper rotation must have determinant +1
    determinant = float(np.linalg.det(rotation))

    # Accept the matrix only when it is orthogonal and has a determinant of +1, within a small tolerance
    valid = orthogonal and np.isclose(
        determinant,
        1.0,
        atol=1e-10,
        rtol=0,
    )

    # Return the individual checks and the overall validity as a dictionary
    return {
        "orthogonal": bool(orthogonal),
        "determinant": determinant,
        "valid": bool(valid),
    }