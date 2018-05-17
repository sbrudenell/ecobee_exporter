import logging

import ecobee
import prometheus_client


class EcobeeCollector(object):

    def __init__(self, api_key, authfile):
        self.api_key = api_key
        self.authfile = authfile
        self._prefix = "ecobee_"
        self._log = logging.getLogger(__name__)

    def make_metric(self, _name, _documentation, _value, **_labels):
        label_names = list(_labels.keys())
        metric = prometheus_client.core.GaugeMetricFamily(
            _name, _documentation or "No Documentation", labels=label_names)
        metric.add_metric([str(_labels[k]) for k in label_names], _value)
        return metric

    def collect(self):
        metrics = []
        api = ecobee.Client(self.api_key, scope="smartRead",
                authfile=self.authfile)
        if api.authentication_required:
            self._log.error("API key not authenticated. Terminating.")
        for thermostat in api.list_thermostats():
            thermostat_id = {
                "thermostat_id": thermostat.id,
                "thermostat_name": thermostat.name}
            running = [eq for eq in thermostat.running.split(",") if eq]
            for equipment in running:
                labels = {"equipment": equipment}
                labels.update(thermostat_id)
                metrics.append(self.make_metric(
                    self._prefix + "running",
                    "Whether equipment is running",
                    1,
                    **labels))
            for k, v in thermostat.settings.items():
                labels = dict(thermostat_id)
                try:
                    v = float(v)
                except ValueError:
                    pass
                if type(v) is str:
                    labels["value"] = v
                    v = 1.0
                elif type(v) is not float:
                    self._log.debug("ignoring setting %s = %r", k, v)
                    continue
                metrics.append(self.make_metric(
                    self._prefix + "setting_" + k,
                    "Ecobee Settings",
                    v,
                    **labels))
            for k in ("actualHumidity", "desiredHumidity",
                    "desiredDehumidity"):
                if k not in thermostat.runtime:
                    self._log.debug("expected metric not found: %s", k)
                    continue
                metrics.append(self.make_metric(
                    self._prefix + "runtime_" + k,
                    "Ecobee Runtime Metrics",
                    thermostat.runtime[k],
                    **thermostat_id))
            for k in ("actualTemperature", "desiredCool", "desiredHeat"):
                if k not in thermostat.runtime:
                    self._log.debug("expected metric not found: %s", k)
                    continue
                metrics.append(self.make_metric(
                    self._prefix + "runtime_" + k,
                    "Ecobee Runtime Metrics",
                    thermostat.runtime[k] / 10.0,
                    **thermostat_id))
            for k in ("desiredCoolRange", "desiredHeatRange"):
                if k not in thermostat.runtime:
                    self._log.debug("expected metric not found: %s", k)
                    continue
                v = thermostat.runtime[k]
                metrics.append(self.make_metric(
                    self._prefix + "runtime_" + k + "_lo",
                    "Ecobee Runtime Metrics",
                    v[0] / 10.0,
                    **thermostat_id))
                metrics.append(self.make_metric(
                    self._prefix + "runtime_" + k + "_hi",
                    "Ecobee Runtime Metrics",
                    v[1] / 10.0,
                    **thermostat_id))

            for sensor in thermostat.list_sensors():
                sensor_id = {
                    "sensor_id": sensor.id,
                    "sensor_name": sensor.name,
                    "sensor_type": sensor.type}
                sensor_id.update(thermostat_id)
                if sensor.temperature is not None:
                    metrics.append(self.make_metric(
                        self._prefix + "temperature",
                        "Sensor Temperature",
                        sensor.temperature,
                        **sensor_id))
                if sensor.humidity is not None:
                    metrics.append(self.make_metric(
                        self._prefix + "humidity",
                        "Sensor Humidity",
                        sensor.humidity,
                        **sensor_id))
                if sensor.occupancy is not None:
                    metrics.append(self.make_metric(
                        self._prefix + "occupancy",
                        "Sensor Occupancy",
                        sensor.occupancy,
                        **sensor_id))
        return metrics
