# solar_system_shapiro.py
# Add in Shapiro delays due to solar system objects
import numpy
import astropy.units as u
import astropy.constants as const
from astropy import log
from .parameter import Parameter
from .timing_model import TimingModel
from .. import Tsun, Tmercury, Tvenus, Tearth, Tmars, \
        Tjupiter, Tsaturn, Turanus, Tneptune

class SolarSystemShapiro(TimingModel):

    def __init__(self):
        super(SolarSystemShapiro, self).__init__()

        self.add_param(Parameter(name="PLANET_SHAPIRO",
            units=None, value=True, continuous=False,
            description="Include planetary Shapiro delays (Y/N)",
            parse_value=lambda x: x.upper() == 'Y',
            print_value=lambda x: 'Y' if x else 'N'))

        self.delay_funcs += [self.solar_system_shapiro_delay,]

    def setup(self):
        super(SolarSystemShapiro, self).setup()

    # Put masses in a convenient dictionary
    _ss_mass_sec = {"sun": Tsun.value,
                    "mercury": Tmercury.value,
                    "venus": Tvenus.value,
                    "earth": Tearth.value,
                    "mars": Tmars.value,
                    "jupiter": Tjupiter.value,
                    "saturn": Tsaturn.value,
                    "uranus": Turanus.value,
                    "neptune": Tneptune.value}

    @staticmethod
    def ss_obj_shapiro_delay(obj_pos, psr_dir, T_obj):
        """
        ss_obj_shapiro_delay(obj_pos, psr_dir, T_obj)

        returns Shapiro delay in seconds for a solar system object.

        Inputs:
          obj_pos : position vector from Earth to SS object, with Units
          psr_dir : unit vector in direction of pulsar
          T_obj : mass of object in seconds (GM/c^3)
        """
        # TODO: numpy.sum currently loses units in some cases...
        r = (numpy.sqrt(numpy.sum(obj_pos**2, axis=1))) * obj_pos.unit
        rcostheta = numpy.sum(obj_pos*psr_dir, axis=1)
        # This formula copied from tempo2 code.  The sign of the
        # cos(theta) term has been changed since we are using the
        # opposite convention for object position vector (from
        # observatory to object in this code).
        # Tempo2 use the postion vector sign differently between the sun and planets
        return -2.0 * T_obj * numpy.log((r-rcostheta)/const.au).value

    def solar_system_shapiro_delay(self, toas):
        """
        Returns total shapiro delay to due solar system objects.
        If the PLANET_SHAPIRO model param is set to True then
        planets are included, otherwise only the value for the
        Sun is calculated.

        Requires Astrometry or similar model that provides the
        ssb_to_psb_xyz method for direction to pulsar.

        If planets are to be included, TOAs.compute_posvels() must
        have been called with the planets=True argument.
        """
        # Start out with 0 delay with units of seconds
        delay = numpy.zeros(len(toas))
        for ii, key in enumerate(toas.groups.keys):
            grp = toas.groups[ii]
            obs = toas.groups.keys[ii]['obs']
            loind, hiind = toas.groups.indices[ii:ii+2]
            if key['obs'] == 'Barycenter':
                log.info("Skipping Shapiro delay for Barycentric TOAs")
                continue

            psr_dir = self.ssb_to_psb_xyz(epoch=grp['tdbld'].astype(numpy.float64))
            delay[loind:hiind] += self.ss_obj_shapiro_delay(grp['obs_sun_pos'],
                                    psr_dir, self._ss_mass_sec['sun'])
            if self.PLANET_SHAPIRO.value:
                for pl in ('jupiter', 'saturn', 'venus', 'uranus'):
                    delay[loind:hiind] += self.ss_obj_shapiro_delay(grp['obs_'+pl+'_pos'],
                                                   psr_dir, self._ss_mass_sec[pl])
        return delay
