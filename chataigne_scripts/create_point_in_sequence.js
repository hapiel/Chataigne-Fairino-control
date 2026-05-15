var j1 = script.addFloatParameter("j1", "Joint 1 angle", 0, -360, 360);
var j2 = script.addFloatParameter("j2", "Joint 2 angle", 0, -360, 360);
var j3 = script.addFloatParameter("j3", "Joint 3 angle", 0, -360, 360);
var j4 = script.addFloatParameter("j4", "Joint 4 angle", 0, -360, 360);
var j5 = script.addFloatParameter("j5", "Joint 5 angle", 0, -360, 360);
var j6 = script.addFloatParameter("j6", "Joint 6 angle", 0, -360, 360);

var triggerAddPoint = script.addTrigger("Add Point", "Adds/replaces control points on all j1-j6 mapping layers at the current time");
var triggerSaveJ1 = script.addTrigger("Save j1", "Adds/replaces a control point on the j1 mapping layer at the current time");
var triggerSaveJ2 = script.addTrigger("Save j2", "Adds/replaces a control point on the j2 mapping layer at the current time");
var triggerSaveJ3 = script.addTrigger("Save j3", "Adds/replaces a control point on the j3 mapping layer at the current time");
var triggerSaveJ4 = script.addTrigger("Save j4", "Adds/replaces a control point on the j4 mapping layer at the current time");
var triggerSaveJ5 = script.addTrigger("Save j5", "Adds/replaces a control point on the j5 mapping layer at the current time");
var triggerSaveJ6 = script.addTrigger("Save j6", "Adds/replaces a control point on the j6 mapping layer at the current time");

var jointParams = [j1, j2, j3, j4, j5, j6];
var saveTriggers = [triggerSaveJ1, triggerSaveJ2, triggerSaveJ3, triggerSaveJ4, triggerSaveJ5, triggerSaveJ6];

function init() {}

function getSequence() {
    var seqEnum = root.customVariables.sequenceEditing.variables.selectedSequence.selectedSequence;
    var seqName = seqEnum.getKey();
    if (!seqName) {
        script.logWarning("No sequence selected!");
        return null;
    }
    var seq = root.sequences.getItemWithName(seqName);
    if (seq == null) {
        script.logError("Sequence not found: " + seqName);
    }
    return seq;
}

function saveJoint(seq, jointIndex, value) {
    var currentTime = seq.getChild("Current Time").get();
    var layer = seq.getChild("layers").getChild("j " + jointIndex);
    if (layer == null) {
        script.logWarning("Layer not found: j " + jointIndex);
        return;
    }
    var existing = layer.automation.getKeysBetween(currentTime - 0.001, currentTime + 0.001);
    for (var k = 0; k < existing.length; k++) {
        layer.automation.removeItem(existing[k]);
    }
    layer.automation.addKey(currentTime, value);
}

function scriptParameterChanged(param) {
    for (var i = 0; i < 6; i++) {
        if (param.is(saveTriggers[i])) {
            var seq = getSequence();
            if (seq == null) return;
            saveJoint(seq, i + 1, jointParams[i].get());
            return;
        }
    }

    if (param.is(triggerAddPoint)) {
        var seq = getSequence();
        if (seq == null) return;
        for (var i = 1; i <= 6; i++) {
            saveJoint(seq, i, jointParams[i - 1].get());
        }
    }
}
