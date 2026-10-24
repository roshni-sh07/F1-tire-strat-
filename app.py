from http.server import BaseHTTPRequestHandler, HTTPServer
import json

PAGE = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>F1 Pit Stop Strategy</title>
  <style>
    :root {
      font-family: Arial, sans-serif;
      color: #17212b;
      background: #f3f5f6;
    }

    * { box-sizing: border-box; }

    body { margin: 0; }

    header {
      background: #102b3f;
      color: white;
      padding: 24px max(22px, calc((100% - 980px) / 2));
    }

    h1 { font-size: 25px; margin: 0 0 7px; }
    header p { margin: 0; color: #d6e0e7; }

    main {
      max-width: 980px;
      margin: 28px auto;
      padding: 0 18px;
    }

    .layout {
      display: grid;
      grid-template-columns: repeat(2, minmax(280px, 1fr));
      gap: 18px;
    }

    section {
      background: white;
      border: 1px solid #d9e0e4;
      padding: 20px;
    }

    h2 { margin: 0 0 16px; font-size: 18px; }

    label {
      display: block;
      font-size: 14px;
      font-weight: 600;
      margin: 13px 0 5px;
    }

    input, select {
      width: 100%;
      padding: 9px 10px;
      border: 1px solid #aebbc3;
      background: white;
      color: #17212b;
      font: inherit;
    }

    .tire {
      padding: 12px;
      border: 1px solid #e0e5e8;
      margin: 10px 0;
    }

    .tire h3 { margin: 0; font-size: 15px; }

    .two {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }

    button {
      margin-top: 17px;
      padding: 10px 15px;
      color: white;
      background: #176b87;
      border: 0;
      font-size: 15px;
      font-weight: 700;
      cursor: pointer;
    }

    button:hover { background: #10546b; }

    #result { min-height: 100px; line-height: 1.5; }

    .summary {
      padding: 12px;
      background: #edf4f6;
      margin-bottom: 14px;
    }

    table { width: 100%; border-collapse: collapse; }

    th, td {
      text-align: left;
      padding: 8px 5px;
      border-bottom: 1px solid #e0e5e8;
    }

    .note {
      color: #566570;
      font-size: 13px;
      line-height: 1.45;
    }

    @media (max-width: 700px) {
      .layout { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <h1>F1 Pit Stop Strategy</h1>
    <p>Compare tire stints using a shortest-path model.</p>
  </header>

  <main>
    <div class="layout">
      <section>
        <h2>Race settings</h2>

        <label for="laps">Race distance (laps)</label>
        <input id="laps" type="number" min="2" max="300" value="30">

        <label for="pitloss">Pit-stop time loss (seconds)</label>
        <input id="pitloss" type="number" min="0" step="0.1" value="22">

        <label for="start">Starting tire</label>
        <select id="start">
          <option>Soft</option>
          <option selected>Medium</option>
          <option>Hard</option>
        </select>

        <h2 style="margin-top:24px">Tire model</h2>
        <p class="note">
          Set each tire's first-lap time and the time added per lap of tire age.
          This simplified model does not include fuel, traffic, weather, or
          safety-car effects.
        </p>

        <div id="tires"></div>
        <button id="calculate">Find fastest strategy</button>
      </section>

      <section>
        <h2>Recommended strategy</h2>
        <div id="result" aria-live="polite">
          Enter race settings and calculate a strategy.
        </div>
      </section>
    </div>
  </main>

  <script>
    const defaults = {
      Soft: [90.0, 0.12],
      Medium: [91.0, 0.07],
      Hard: [92.0, 0.045]
    };

    document.getElementById("tires").innerHTML =
      Object.entries(defaults).map(([name, values]) => `
        <div class="tire">
          <h3>${name}</h3>
          <div class="two">
            <div>
              <label>${name} first-lap time (s)</label>
              <input class="base" data-name="${name}" type="number"
                     step="0.01" value="${values[0]}">
            </div>
            <div>
              <label>Degradation (s per tire-age lap)</label>
              <input class="wear" data-name="${name}" type="number"
                     min="0" step="0.001" value="${values[1]}">
            </div>
          </div>
        </div>
      `).join("");

    document.getElementById("calculate").addEventListener("click", async () => {
      const result = document.getElementById("result");
      result.textContent = "Calculating…";

      const tires = {};

      for (const name of Object.keys(defaults)) {
        tires[name] = {
          base: Number(
            document.querySelector(`.base[data-name="${name}"]`).value
          ),
          wear: Number(
            document.querySelector(`.wear[data-name="${name}"]`).value
          )
        };
      }

      const payload = {
        laps: Number(document.getElementById("laps").value),
        pit_loss: Number(document.getElementById("pitloss").value),
        start: document.getElementById("start").value,
        tires
      };

      try {
        const response = await fetch("/optimize", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.error || "Could not calculate strategy.");
        }

        result.innerHTML = `
          <div class="summary">
            <strong>Estimated race time:</strong>
            ${data.total_time.toFixed(2)} seconds<br>
            <strong>Pit stops:</strong> ${data.stops}
          </div>
          <table>
            <thead>
              <tr><th>Stint</th><th>Tire</th><th>Laps</th></tr>
            </thead>
            <tbody>
              ${data.stints.map((stint, index) => `
                <tr>
                  <td>${index + 1}</td>
                  <td>${stint.tire}</td>
                  <td>${stint.start}–${stint.end}</td>
                </tr>
              `).join("")}
            </tbody>
          </table>
          <p class="note">
            This is a simplified estimate, not live race data.
          </p>
        `;
      } catch (error) {
        result.textContent = error.message;
      }
    });
  </script>
</body>
</html>'''


def optimize(data):
    laps = int(data["laps"])
    pit_loss = float(data["pit_loss"])
    tires = data["tires"]
    names = list(tires)
    start = data["start"]

    if not 2 <= laps <= 300:
        raise ValueError("Race distance must be between 2 and 300 laps.")

    if pit_loss < 0 or start not in names:
        raise ValueError("Choose a valid starting tire and non-negative pit loss.")

    for tire in names:
        base = float(tires[tire]["base"])
        wear = float(tires[tire]["wear"])

        if base <= 0 or wear < 0:
            raise ValueError(
                "Tire times must be positive and degradation cannot be negative."
            )

    # Each state records the tire compound and how old that tire is.
    # Transitions represent either driving another lap or pitting.
    current = {(start, 1): (0.0, None)}
    layers = [current]

    for lap in range(1, laps + 1):
        next_states = {}

        for (compound, age), (cost, _) in current.items():
            # The selected starting tire is used for the first lap.
            compounds = [compound] if lap == 1 else names

            for next_compound in compounds:
                stopping = next_compound != compound
                next_age = 1 if stopping else age + 1

                lap_cost = (
                    float(tires[next_compound]["base"])
                    + float(tires[next_compound]["wear"]) * (next_age - 1)
                )

                candidate = cost + lap_cost
                if stopping:
                    candidate += pit_loss

                key = (next_compound, next_age)

                if key not in next_states or candidate < next_states[key][0]:
                    next_states[key] = (
                        candidate,
                        (compound, age, stopping)
                    )

        current = next_states
        layers.append(current)

    final_state = min(current, key=lambda state: current[state][0])
    total_time = current[final_state][0]

    # Follow the stored previous states to recover the chosen lap sequence.
    path = []
    state = final_state

    for lap in range(laps, 0, -1):
        path.append((lap, state[0], state[1]))
        previous = layers[lap][state][1]

        if previous is None:
            break

        state = (previous[0], previous[1])

    path.reverse()

    stints = []

    for lap, tire, _age in path:
        if not stints or stints[-1]["tire"] != tire:
            stints.append({
                "tire": tire,
                "start": lap,
                "end": lap
            })
        else:
            stints[-1]["end"] = lap

    return {
        "total_time": total_time,
        "stops": max(0, len(stints) - 1),
        "stints": stints
    }


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/":
            self.send_error(404)
            return

        body = PAGE.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/optimize":
            self.send_error(404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length))
            result = optimize(data)
            self.send_json(200, result)
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
            self.send_json(400, {"error": str(error) or "Invalid input."})

    def send_json(self, status, value):
        body = json.dumps(value).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    print("Open http://127.0.0.1:8000 in your browser.")
    HTTPServer(("127.0.0.1", 8000), Handler).serve_forever()