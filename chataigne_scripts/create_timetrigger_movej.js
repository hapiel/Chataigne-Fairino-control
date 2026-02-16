var triggerLayer = script.addTargetParameter("Trigger layer", "The target to use for the moveJ command");
// New Trigger for Arming
var triggerArmJoints = script.addTrigger("Arm j1-j6", "Arms recorders for j1 through j6 in the selected sequence");
var disArmJoints = script.addTrigger("Disarm j1-j6", "Disarms recorders for j1 through j6 in the selected sequence");

var triggerMoveJ = script.addTrigger("Create moveJ", "Creates a moveJ command in the current active sequence");
var defaultSpeed = script.addFloatParameter("Default Speed", "", 70, 0, 100);
var defaultAcceleration = script.addFloatParameter("Default Acceleration log", "", 50, 0, 100);

triggerLayer.setAttribute("root", root.sequences);
triggerLayer.setAttribute("targetType", "container");
triggerLayer.setAttribute("searchLevel", 2);

var yPos = 0;

function init() { }

function scriptParameterChanged(param) {

	// Logic for Arming j1 - j6
	if (param.is(triggerArmJoints) || param.is(disArmJoints)) {
		var seq = triggerLayer.getTarget(); // This gets the actual container object

		if (seq !== null) {
			for (var i = 1; i <= 6; i++) {
				var jointName = "j" + i;
				// Path construction: layers -> j[i] -> recorder -> arm
				var armParam = seq.getParent().getParent().getChild("layers").getChild(jointName).getChild("recorder").getChild("arm");

				if (armParam !== null) {
					if (param.is(triggerArmJoints)) {
						armParam.set(1);
					} else if (param.is(disArmJoints)) {
						armParam.set(0);
					}
				}
			}
		} else {
			script.logWarning("No Sequence Target selected!");
		}
	}

	// Your existing moveJ logic
	if (param.is(triggerMoveJ)) {
		var targetContainer = triggerLayer.getTarget();
		if (targetContainer == null) return;

		var timeCursor = targetContainer.getParent().getParent().getChild("Current Time").get();

		var newTimeTrigger = targetContainer.getChild("Triggers").addItem();
		newTimeTrigger.getChild("Time").set(timeCursor);
		newTimeTrigger.getChild("Flag Y").set(yPos);
		yPos = (yPos + 0.2);
		if (yPos > 1.0) { yPos = 0.0; }

		var jointTargets = ["moveJSpeed", "moveJAcceleration", "j1", "j2", "j3", "j4", "j5", "j6"];
		var jointValues = [
			defaultSpeed.get(),
			defaultAcceleration.get(),
			local.values._j_pos_0.get(),
			local.values._j_pos_1.get(),
			local.values._j_pos_2.get(),
			local.values._j_pos_3.get(),
			local.values._j_pos_4.get(),
			local.values._j_pos_5.get()
		];

		for (var i = 0; i < jointTargets.length; i++) {
			var consequence = newTimeTrigger.getChild("Consequences").addItem("Consequence");
			consequence.setName(jointTargets[i]);
			var command = consequence.setCommand("customVariables", "", "Set Value");

			var params = {
				parameters: [
					{ value: "/TargetJointAngles/" + jointTargets[i], controlAddress: "/target" },
					{ value: "All", controlAddress: "/component" },
					{ value: "Equals", controlAddress: "/operator" },
					{ value: jointValues[i], controlAddress: "/value" }
				],
				paramLinks: {}
			};
			command.loadJSONData(params);
		}

		var consequenceAction = newTimeTrigger.getChild("Consequences").addItem("Consequence");
		var commandAction = consequenceAction.setCommand("stateMachine", "Action", "Trigger Action");
		commandAction.getChild("Target").set("/states/move/processors/moveJ");
	}
}