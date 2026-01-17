package glasses

import android.content.Context

class GlassesAudioDiagnostics(private val context: Context) {
    private val routeMonitor = AudioRouteMonitor(context)

    fun routeSummary(): String = routeMonitor.currentRouteSummary()
}
