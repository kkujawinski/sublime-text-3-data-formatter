(function() {
    "use strict";

    var exitCode;

    process.stdin.on(
        'data',
        function(text) {
            try {
                var output = JSON.stringify(
                  JSON.parse(text), null, 4
                );
                process.stdout.write(output);
                exitCode = 0
            } catch (ex) {
                process.stdout.write(ex.message);
                exitCode = 1;
            }
        }
    );

    process.on("exit", function() {
        process.exit(exitCode);
    });
})();
