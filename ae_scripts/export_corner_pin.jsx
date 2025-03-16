(function(){
    // --- Polyfills for ExtendScript ---

    // Polyfill for Array.isArray if not available
    if (typeof Array.isArray !== "function") {
        Array.isArray = function(arg) {
            return Object.prototype.toString.call(arg) === '[object Array]';
        };
    }
    
    // Polyfill for JSON.stringify if not available
    if (typeof JSON === "undefined") {
        JSON = {};
    }
    if (typeof JSON.stringify !== "function") {
        JSON.stringify = function(value) {
            var type = typeof value;
            if (value === null) {
                return "null";
            }
            if (type === "number" || type === "boolean") {
                return String(value);
            }
            if (type === "string") {
                // Escape backslashes and quotes for a basic implementation.
                return '"' + value.replace(/\\/g, '\\\\').replace(/"/g, '\\"') + '"';
            }
            if (Array.isArray(value)) {
                var arrayContent = [];
                for (var i = 0; i < value.length; i++) {
                    arrayContent.push(JSON.stringify(value[i]));
                }
                return '[' + arrayContent.join(',') + ']';
            }
            if (type === "object") {
                var props = [];
                for (var key in value) {
                    if (value.hasOwnProperty(key)) {
                        props.push(JSON.stringify(key) + ':' + JSON.stringify(value[key]));
                    }
                }
                return '{' + props.join(',') + '}';
            }
            // If value type is not supported, return undefined.
            return undefined;
        };
    }
    
    // --- Main Script ---

    // Ensure a project is open and an active comp is selected.
    if (!app.project) {
        alert("No project open.");
        return;
    }
    if (!(app.project.activeItem instanceof CompItem)) {
        alert("Please select a composition.");
        return;
    }
    
    var comp = app.project.activeItem;
    
    // Locate the layer named "source"
    var sourceLayer = comp.layer("source");
    if (!sourceLayer) {
        alert("Layer named 'source' not found.");
        return;
    }
    
    // Access the Corner Pin effect on the layer.
    var cornerPinEffect = sourceLayer.effect("Corner Pin");
    if (!cornerPinEffect) {
        alert("Corner Pin effect not found on layer 'source'.");
        return;
    }
    
    // Retrieve the four corner properties.
    var ulProp = cornerPinEffect.property("Upper Left");
    var urProp = cornerPinEffect.property("Upper Right");
    var lrProp = cornerPinEffect.property("Lower Right");
    var llProp = cornerPinEffect.property("Lower Left");
    
    if (!ulProp || !urProp || !lrProp || !llProp) {
        alert("One or more corner properties could not be found.");
        return;
    }
    
    // Use the composition's frame rate to determine the number of frames.
    var fps = comp.frameRate;
    var numFrames = Math.floor(comp.duration * fps);
    
    // Create an object to store the corner pin data per frame.
    var data = {};
    
    // Loop through each frame, sampling the four corner values.
    for (var f = 0; f < numFrames; f++) {
        var time = f / fps;
        
        // Sample each corner's value at the given time.
        // The second parameter 'false' means we do not force an interpolation.
        var ul = ulProp.valueAtTime(time, false);
        var ur = urProp.valueAtTime(time, false);
        var lr = lrProp.valueAtTime(time, false);
        var ll = llProp.valueAtTime(time, false);
        
        // Store the data for the frame.
        data[f] = {
            "ul": [ul[0], ul[1]],
            "ur": [ur[0], ur[1]],
            "lr": [lr[0], lr[1]],
            "ll": [ll[0], ll[1]]
        };
    }
    
    // Convert the data object to a JSON string.
    var jsonStr = JSON.stringify(data);
    
    // Prompt the user to choose a location to save the JSON file.
    var saveFile = File.saveDialog("Save JSON", "*.json");
    if (saveFile !== null) {
        saveFile.open("w");
        saveFile.write(jsonStr);
        saveFile.close();
        alert("JSON exported to " + saveFile.fsName);
    }
})();
