var maxSpeed = script.addFloatParameter(
	"max Speed",
	"maximum speed in degrees /s",
	180, 0, 360
);

var maxAcceleration = script.addFloatParameter(
	"max Acceleration",
	"maximum acceleration in degrees /s^2",
	360, 0, 8000
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
	if (dT > 0.3) {
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

		// --- MAX SAFE VELOCITY TO STOP AT TARGET ---
		var vMax = Math.sqrt(2 * maxAcceleration.get() * Math.abs(distance));
		if (distance < 0) vMax = -vMax;

		// compute dv and clamp by maxAcceleration
		var dv = vMax - vel;
		var maxDv = maxAcceleration.get() * dT;
		if (dv > maxDv) dv = maxDv;
		else if (dv < -maxDv) dv = -maxDv;

		vel += dv;

		// clamp velocity to maxSpeed
		var maxSpd = maxSpeed.get();
		if (vel > maxSpd) vel = maxSpd;
		else if (vel < -maxSpd) vel = -maxSpd;

		// integrate position
		pos += vel * dT;

		result[i] = pos;
		previousInputs[i] = pos;
		velocities[i] = vel;
	}

	return result;
}
