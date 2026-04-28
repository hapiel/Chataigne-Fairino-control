var maxSpeedBase = script.addFloatParameter(
	"max Speed j1-3",
	"maximum speed in degrees /s",
	140, 0, 150
);


var maxSpeed = script.addFloatParameter(
	"max Speed j4-6 ",
	"maximum speed in degrees /s",
	150, 0, 180
);

var maxAccelerationBase = script.addFloatParameter(
	"max Acceleration j1-3",
	"maximum acceleration in degrees /s^2 for bottom stuff",
	360, 0, 1000
);

var maxAcceleration = script.addFloatParameter(
	"max Acceleration  j4-6",
	"maximum acceleration in degrees /s^2",
	360, 0, 4000
);



// NEW: small distance threshold to clamp to target
var targetDeadzone = script.addFloatParameter(
	"Target Deadzone",
	"distance to target below which value is clamped",
	0.05, 0, 1
);

var previousInputs = [];
var velocities = [];
var lastTime = -1;

function filter(inputs, minValues, maxValues, multiplexIndex) {
	var nowMs = util.getTime();

	var dT;
	if (lastTime < 0) {
		dT = 1 / 50; // fallback first frame
	} else {
		dT = (nowMs - lastTime);
		if (dT <= 0) dT = 1e-4; // safety
	}

	// --- LARGE DT PROTECTION ---
	if (dT > 0.5) {
		lastTime = nowMs;

		// copy inputs to previousInputs
		previousInputs = [];
		velocities = [];
		for (var j = 0; j < inputs.length; j++) {
			previousInputs[j] = inputs[j];
			velocities[j] = 0;
		}

		// return inputs directly
		var result = [];
		for (var j = 0; j < inputs.length; j++) {
			result[j] = inputs[j];
		}
		return result;
	}

	lastTime = nowMs;
	var result = [];

	for (var i = 0; i < inputs.length; i++) {
		if (previousInputs.length <= i) {
			previousInputs[i] = inputs[i];
			velocities[i] = 0;
		}

		var pos = previousInputs[i];
		var vel = velocities[i];
		var target = inputs[i];

		var distance = target - pos;

		// --- DEADZONE NEAR TARGET ---
		if (Math.abs(distance) <= targetDeadzone.get()) {
			pos = target;
			vel = 0;
			result[i] = pos;
			previousInputs[i] = pos;
			velocities[i] = vel;
			continue;
		}

		// --- SELECT LIMITS BASED ON JOINT INDEX ---
		// i < 3 → joints 1-3 (Base params), i >= 3 → joints 4-6 (standard params)
		var accelLimit = (i < 3) ? maxAccelerationBase.get() : maxAcceleration.get();
		var speedLimit = (i < 3) ? maxSpeedBase.get() : maxSpeed.get();

		// --- MAX SAFE VELOCITY TO STOP AT TARGET ---
		var vMax = Math.sqrt(2 * accelLimit * Math.abs(distance));
		if (distance < 0) vMax = -vMax;

		// compute dv and clamp by accelLimit
		var dv = vMax - vel;
		var maxDv = accelLimit * dT;
		if (dv > maxDv) dv = maxDv;
		else if (dv < -maxDv) dv = -maxDv;
		vel += dv;

		// clamp velocity to speedLimit
		if (vel > speedLimit) vel = speedLimit;
		else if (vel < -speedLimit) vel = -speedLimit;

		// integrate position
		pos += vel * dT;

		result[i] = pos;
		previousInputs[i] = pos;
		velocities[i] = vel;
	}

	return result;
}
