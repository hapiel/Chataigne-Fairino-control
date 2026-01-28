
var sequenceTarget = script.addTargetParameter("Sequence Target", "The target to use for the moveJ command");
var triggerMoveJ = script.addTrigger("Create moveJ", "Creates a moveJ command in the current active sequence");
var defaultSpeed = script.addFloatParameter("Default Speed", "", 60, 0, 360);
var defaultAcceleration = script.addFloatParameter("Default Acceleration log", "", 40, 0, 100);

sequenceTarget.setAttribute("root", root.sequences);
sequenceTarget.setAttribute("targetType", "container");
sequenceTarget.setAttribute("searchLevel", 2);


var yPos = 0;



function init() {


}

/*
  This function will be called each time a parameter of your script has changed
*/
function scriptParameterChanged(param) {
	if (param.is(triggerMoveJ)) {

		var timeCursor = sequenceTarget.getTarget().getParent().getParent().getChild("Current Time").get();

		newTimeTrigger = sequenceTarget.getTarget().getChild("Triggers").addItem();
		newTimeTrigger.getChild("Time").set(timeCursor);
		newTimeTrigger.getChild("Flag Y").set(yPos);
		yPos = (yPos + 0.2);
		if (yPos > 1.0) {
			yPos = 0.0;
		}

		var jointTargets = ["speed", "accLog", "base", "shoulder", "elbow", "wrist1", "wrist2", "wrist3"];

		// Define unique values (example numbers, replace with yours)
		var jointValues = [defaultSpeed.get(), defaultAcceleration.get(), local.values._joints_0.get(), local.values._joints_1.get(), local.values._joints_2.get(), local.values._joints_3.get(), local.values._joints_4.get(), local.values._joints_5.get()];

		// Loop over joints
		for (var i = 0; i < jointTargets.length; i++) {
			var consequence = newTimeTrigger.getChild("Consequences").addItem("Consequence");
			consequence.setName(jointTargets[i]);
			var command = consequence.setCommand("customVariables", "", "Set Value");

			var params = {
				parameters: [
					{ value: "/targetJointAngles/" + jointTargets[i], controlAddress: "/target" },
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
		// commandModule, commandPath, commandType

		commandAction.getChild("Target").set("/states/actions/processors/moveJAtSpeed");



	}
}

// {
//   "niceName": "Consequence 1",
//   "type": "Consequence",
//   "commandModule": "customVariables",
//   "commandPath": "",
//   "commandType": "Set Value",
//   "command": {
//     "parameters": [
//       {
//         "value": "",
//         "controlAddress": "/target"
//       }
//     ],
//     "paramLinks": {
//     }
//   }
// }


//GetControllables output: [[Enabled : Boolean > 1], [MiniMode : Boolean > 0], [ListSize : Float > 24.000], [ViewUIPosition : Point2D > [0.0,0.0]], [ViewUISize : Point2D > [200.0,200.0]], [Locked : Boolean > 0], [Trigger : Trigger]]

// 10:58:36.923	Script : create_timetrigger_movej	[[Enabled : Boolean > 1], [MiniMode : Boolean > 0], [ListSize : Float > 24.000], [ViewUIPosition : Point2D > [0.0,0.0]], [ViewUISize : Point2D > [200.0,200.0]], [Locked : Boolean > 0], [Trigger : Trigger]]