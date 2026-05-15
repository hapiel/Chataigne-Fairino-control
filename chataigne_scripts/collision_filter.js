// =====================================================================
// ROBOT ARM COLLISION FILTER
// 6-axis robot, joint order: J1–J6 (index 0–5). Angles in degrees.
// =====================================================================

// ---- LOGIC ----
// Each joint independently checks: "is my new position legal given
// where the other joints currently are?" If yes, move. If no, stay.
//
// The collision zone rule:
//   J3 < -103 is only permitted when AT LEAST ONE of:
//     • J4 > -105
//     • J5 < 44
//     • J5 > 115
//
// A safety margin shrinks all thresholds inward.
//
// J3 hard floor: J3 can never go below -150.
//
// J5 band-crossing prevention:
//   When J3 is in the danger zone, J5 is locked to whichever side of
//   [44, 115] it is currently on. It cannot cross to the other side
//   regardless of where the input goes. It unlocks when J3 is freed.
// =====================================================================

var safetyParam = script.addFloatParameter(
  "Safety Margin",
  "Degrees of buffer added to all collision thresholds.",
  5, 0, 20
);

var previousJoints = [];
var j5BlockedSide = 0; // -1 = on low side, +1 = on high side, 0 = free

function filter(inputs, minValues, maxValues, multiplexIndex) {
  var i;
  var safety = safetyParam.get();
  var joints = [];
  for (i = 0; i < 6; i++) {
    joints[i] = (inputs[i] !== undefined) ? inputs[i] : 0;
  }

  if (previousJoints.length === 0) {
    for (i = 0; i < 6; i++) previousJoints[i] = joints[i];
  }

  var j3 = previousJoints[2];
  var j4 = previousJoints[3];
  var j5 = previousJoints[4];

  var j3Threshold = -103 + safety;
  var j5Low       =   44 - safety;
  var j5High      =  115 + safety;
  var j4Threshold = -105 + safety;

  function hatchOpen(testJ4, testJ5) {
    return testJ4 > j4Threshold || testJ5 < j5Low || testJ5 > j5High;
  }

  // ---- J3 ----
  var newJ3 = joints[2];
  if (newJ3 < -150) newJ3 = -150;
  if (newJ3 < j3Threshold && !hatchOpen(j4, j5)) {
    newJ3 = j3;
  }
  j3 = newJ3;

  // ---- J4 ----
  var newJ4 = joints[3];
  if (j3 < j3Threshold && !hatchOpen(newJ4, j5)) {
    newJ4 = j4;
  }
  j4 = newJ4;

  // ---- J5 ----
  var newJ5 = joints[4];
  var j3InDanger = (j3 < j3Threshold);

  if (j3InDanger) {
    // First: record which side J5 is currently on (from settled position).
    if (j5 < j5Low)       j5BlockedSide = -1;  // low side
    else if (j5 > j5High) j5BlockedSide =  1;  // high side
    // (if j5 is inside the band already, j5BlockedSide keeps its last value)

    // Now enforce: J5 must stay on its current side.
    // Clamp newJ5 to not cross the band boundary it's locked against.
    if (j5BlockedSide === -1) {
      // Locked on low side — cannot go above j5Low
      if (newJ5 > j5Low) newJ5 = j5Low;
    } else if (j5BlockedSide === 1) {
      // Locked on high side — cannot go below j5High
      if (newJ5 < j5High) newJ5 = j5High;
    }
  } else {
    // J3 is free — J5 unlocks.
    j5BlockedSide = 0;
  }
  j5 = newJ5;

  previousJoints[2] = j3;
  previousJoints[3] = j4;
  previousJoints[4] = j5;

  var result = [];
  for (i = 0; i < inputs.length; i++) {
    if      (i === 2) result[i] = j3;
    else if (i === 3) result[i] = j4;
    else if (i === 4) result[i] = j5;
    else              result[i] = joints[i];
  }
  return result;
}